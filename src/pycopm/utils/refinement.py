# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,E1102

"""Refine a corner-point grid and its reservoir properties."""

import argparse
import sys
from contextlib import nullcontext
from dataclasses import dataclass

import numpy as np
from alive_progress import alive_bar
from numpy.typing import NDArray

from pycopm.config.config import ConfigViaDeck
from pycopm.utils.files_writer import write_grid, write_property_inc
from pycopm.utils.input_values import parse_axis_modifications


@dataclass(slots=True)
class RefinementMaps:
    """Store axis refinement values and subdivision counts."""

    #: Number of additional cells created from each original x interval.
    x: NDArray

    #: Number of additional cells created from each original y interval.
    y: NDArray

    #: Number of additional cells created from each original z interval.
    z: NDArray

    #: Number of refined cells generated from each original cell, flattened in
    #: ``(z, y, x)`` order.
    refined_cell_counts: NDArray


def create_refinement_maps(
    dck: ConfigViaDeck, cmdargs: argparse.Namespace
) -> RefinementMaps:
    """Create axis refinement maps and update output dimensions.

    A refinement value of ``n`` divides an original interval into ``n + 1``
    intervals.

    Parameters
    ----------
    dck
        Deck configuration whose output dimensions are updated.
    cmdargs
        Command arguments containing ``refinement``, ``x_refinement``,
        ``y_refinement``, and ``z_refinement``.

    Returns
    -------
    RefinementMaps
        Axis values and the number of subdivisions per original cell."""
    cijk, refs = parse_axis_modifications(
        cmdargs.refinement,
        [
            cmdargs.x_refinement,
            cmdargs.y_refinement,
            cmdargs.z_refinement,
        ],
    )
    values = []
    for direction_index, direction in enumerate(("x", "y", "z")):
        original_size = getattr(dck, f"original_n{direction}")
        if len(cijk) > 2:
            refinement_values = np.full(
                original_size, int(cijk[direction_index]), dtype=int
            )
        elif len(refs[direction_index]) > 0:
            refinement_values = np.asarray(refs[direction_index], dtype=int)
        else:
            refinement_values = np.zeros(original_size, dtype=int)
        values.append(refinement_values)
        setattr(
            dck,
            f"output_n{direction}",
            original_size + int(np.sum(refinement_values)),
        )
    x_repetitions = values[0] + 1
    y_repetitions = values[1] + 1
    z_repetitions = values[2] + 1
    refined_cell_counts = (
        (
            z_repetitions[:, None, None]
            * y_repetitions[None, :, None]
            * x_repetitions[None, None, :]
        )
        .ravel()
        .astype(float)
    )
    return RefinementMaps(
        x=values[0], y=values[1], z=values[2], refined_cell_counts=refined_cell_counts
    )


def refine_properties(
    dck: ConfigViaDeck, refinement: RefinementMaps, modified_deck: list[str]
) -> None:
    """Map reservoir properties onto the refined grid.

    Properties are copied to generated cells. ``PORV`` is divided equally among
    them to preserve each original cell's pore volume.

    Parameters
    ----------
    dck
        Deck configuration containing source properties and output dimensions.
    refinement
        Refinement maps created by :func:`create_refinement_maps`.
    modified_deck
        Deck lines updated with generated property includes."""
    number_values = dck.output_nx * dck.output_ny * dck.output_nz
    property_names = (
        dck.props_keywords
        + dck.regions_keywords
        + ["porv"]
        + dck.grids_keywords
        + dck.solution_keywords
    )
    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_status = alive_bar(len(property_names), bar="fish")
    else:
        bar_status = nullcontext()
    x_repetitions = np.asarray(refinement.x, dtype=np.intp) + 1
    y_repetitions = np.asarray(refinement.y, dtype=np.intp) + 1
    z_repetitions = np.asarray(refinement.z, dtype=np.intp) + 1
    with bar_status as bar_animation:
        for property_name in property_names:
            if show_progress:
                bar_animation()
            if property_name == "porv":
                values = np.divide(
                    np.asarray(dck.init_file[property_name.upper()]),
                    refinement.refined_cell_counts,
                )
            else:
                values = np.zeros(dck.original_cell_count)
                if property_name in dck.solution_keywords:
                    values[dck.original_active_cell_mask] = dck.restart_file[
                        property_name.upper(), 0
                    ]
                else:
                    values[dck.original_active_cell_mask] = dck.init_file[
                        property_name.upper()
                    ]
            output_dtype = int if "num" in property_name else float
            coarse_values = values.reshape(
                dck.original_nz, dck.original_ny, dck.original_nx
            )
            refined_values = (
                np.repeat(
                    np.repeat(
                        np.repeat(coarse_values, x_repetitions, axis=2),
                        y_repetitions,
                        axis=1,
                    ),
                    z_repetitions,
                    axis=0,
                )
                .reshape(number_values)
                .astype(output_dtype, copy=False)
            )
            if property_name == "porv":
                dck.output_actnum = (refined_values > 0).astype(int)
            write_property_inc(
                dck,
                property_name,
                refined_values,
                number_values,
                modified_deck,
                True,
            )


def create_coord_axis_map(
    refinement_values: NDArray,
) -> tuple[NDArray, NDArray]:
    """Create interpolation data for one COORD axis.

    Parameters
    ----------
    refinement_values
        Number of additional cells in each original interval.

    Returns
    -------
    source_indices, fractions
        Original intervals and relative positions of refined grid points."""
    interval_counts = refinement_values + 1
    source_indices = np.repeat(
        np.arange(refinement_values.size, dtype=np.intp),
        interval_counts,
    )
    fraction_blocks = [
        np.arange(interval_count, dtype=float) / interval_count
        for interval_count in interval_counts
    ]
    source_indices = np.concatenate(
        (
            source_indices,
            np.asarray([refinement_values.size - 1], dtype=np.intp),
        )
    )
    fractions = np.concatenate(
        (
            *fraction_blocks,
            np.asarray([1.0]),
        )
    )
    return source_indices, fractions


def create_zcorn_axis_map(
    refinement_values: NDArray,
) -> tuple[NDArray, NDArray]:
    """Create interpolation data for one ZCORN axis.

    Parameters
    ----------
    refinement_values
        Number of additional cells in each original interval.

    Returns
    -------
    source_indices, fractions
        Original intervals and relative corner positions in ZCORN order."""
    interval_counts = refinement_values + 1
    source_indices = np.repeat(
        np.arange(refinement_values.size, dtype=np.intp),
        2 * interval_counts,
    )
    fraction_blocks = [
        np.repeat(
            np.arange(interval_count + 1, dtype=float) / interval_count,
            2,
        )[1:-1]
        for interval_count in interval_counts
    ]
    fractions = np.concatenate(fraction_blocks)
    return source_indices, fractions


def refine_zcorn_surface(
    source_surface: NDArray,
    destination_surface: NDArray,
    original_nx: int,
    original_ny: int,
    output_nx: int,
    output_ny: int,
    zcorn_x_indices: NDArray,
    zcorn_y_indices: NDArray,
    zcorn_x_fractions: NDArray,
    zcorn_y_fractions: NDArray,
) -> None:
    """Interpolate one ZCORN surface onto the refined horizontal grid.

    Parameters
    ----------
    source_surface
        Flattened input surface with ``4 * original_nx * original_ny`` values.
    destination_surface
        Preallocated output with ``4 * output_nx * output_ny`` values, modified
        in place.
    original_nx, original_ny
        Original horizontal grid dimensions.
    output_nx, output_ny
        Refined horizontal grid dimensions.
    zcorn_x_indices, zcorn_y_indices
        Source interval indices for refined corners.
    zcorn_x_fractions, zcorn_y_fractions
        Relative interpolation positions within source intervals."""
    source_values = source_surface.reshape(
        original_ny,
        2,
        original_nx,
        2,
    )
    x_start_values = source_values[:, :, zcorn_x_indices, 0]
    x_value_difference = source_values[:, :, zcorn_x_indices, 1] - x_start_values
    x_refined_values = (
        x_start_values + zcorn_x_fractions[None, None, :] * x_value_difference
    )
    y_start_values = x_refined_values[zcorn_y_indices, 0, :]
    y_value_difference = x_refined_values[zcorn_y_indices, 1, :] - y_start_values
    destination_values = destination_surface.reshape(
        2 * output_ny,
        2 * output_nx,
    )
    np.multiply(
        y_value_difference,
        zcorn_y_fractions[:, None],
        out=destination_values,
    )
    destination_values += y_start_values


def refine_grid(dck: ConfigViaDeck, refinement: RefinementMaps) -> None:
    """Create and write the refined corner-point grid.

    ``COORD`` and ``ZCORN`` values are linearly interpolated along the refined
    axes.

    Parameters
    ----------
    dck
        Deck configuration containing original geometry and grid dimensions.
    refinement
        Axis refinement maps."""
    original_zcorn = np.asarray(dck.egrid_file["ZCORN"], dtype=float)
    original_coord = np.asarray(dck.egrid_file["COORD"], dtype=float)
    x_refinement = np.asarray(refinement.x, dtype=np.intp)
    y_refinement = np.asarray(refinement.y, dtype=np.intp)
    z_refinement = np.asarray(refinement.z, dtype=np.intp)

    coord_x_indices, coord_x_fractions = create_coord_axis_map(x_refinement)
    coord_y_indices, coord_y_fractions = create_coord_axis_map(y_refinement)
    source_coord = original_coord.reshape(
        dck.original_ny + 1,
        dck.original_nx + 1,
        6,
    )
    x_start_coord = source_coord[:, coord_x_indices, :]
    x_coord_difference = source_coord[:, coord_x_indices + 1, :] - x_start_coord
    x_refined_coord = (
        x_start_coord + coord_x_fractions[None, :, None] * x_coord_difference
    )
    y_start_coord = x_refined_coord[coord_y_indices, :, :]
    y_coord_difference = x_refined_coord[coord_y_indices + 1, :, :] - y_start_coord
    refined_coord = (
        y_start_coord + coord_y_fractions[:, None, None] * y_coord_difference
    )
    cr = refined_coord.ravel()

    zcorn_x_indices, zcorn_x_fractions = create_zcorn_axis_map(x_refinement)
    zcorn_y_indices, zcorn_y_fractions = create_zcorn_axis_map(y_refinement)
    source_surface_size = 4 * dck.original_nx * dck.original_ny
    refined_surface_size = 4 * dck.output_nx * dck.output_ny
    refined_zcorn_size = 8 * dck.output_nx * dck.output_ny * dck.output_nz
    source_surfaces = original_zcorn.reshape(
        2 * dck.original_nz,
        source_surface_size,
    )
    zc = np.empty(refined_zcorn_size, dtype=float)

    refined_top_surface = np.empty(
        refined_surface_size,
        dtype=float,
    )
    refined_bottom_surface = np.empty(
        refined_surface_size,
        dtype=float,
    )
    output_index = 0

    original_nx = dck.original_nx
    original_ny = dck.original_ny
    output_nx = dck.output_nx
    output_ny = dck.output_ny
    for layer_index, refinement_value in enumerate(z_refinement):
        refinement_count = int(refinement_value) + 1
        refine_zcorn_surface(
            source_surfaces[2 * layer_index],
            refined_top_surface,
            original_nx,
            original_ny,
            output_nx,
            output_ny,
            zcorn_x_indices,
            zcorn_y_indices,
            zcorn_x_fractions,
            zcorn_y_fractions,
        )
        refine_zcorn_surface(
            source_surfaces[2 * layer_index + 1],
            refined_bottom_surface,
            original_nx,
            original_ny,
            output_nx,
            output_ny,
            zcorn_x_indices,
            zcorn_y_indices,
            zcorn_x_fractions,
            zcorn_y_fractions,
        )
        surface_difference = refined_bottom_surface - refined_top_surface
        vertical_fractions = np.repeat(
            np.arange(
                refinement_count + 1,
                dtype=float,
            )
            / refinement_count,
            2,
        )[1:-1]

        for vertical_fraction in vertical_fractions:
            output_surface = zc[output_index : output_index + refined_surface_size]
            if vertical_fraction == 0.0:
                np.copyto(output_surface, refined_top_surface)
            elif vertical_fraction == 1.0:
                np.copyto(output_surface, refined_bottom_surface)
            else:
                np.multiply(
                    surface_difference,
                    vertical_fraction,
                    out=output_surface,
                )
                output_surface += refined_top_surface
            output_index += refined_surface_size

    write_grid(dck, cr, zc, False)
