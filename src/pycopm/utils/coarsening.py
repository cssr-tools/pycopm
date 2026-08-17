# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0902,R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,E1102

"""Coarsen corner-point grids and aggregate reservoir properties.

The module supports deck-based coarsening and the TOML workflows used to
generate reduced Norne and Drogon models."""

import argparse
import csv
import re
import sys
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from alive_progress import alive_bar
from numpy.typing import NDArray
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid
from opm.io.ecl import ERst as OpmRestart

from pycopm.config.config import ConfigViaDeck, ConfigViaTOML
from pycopm.utils.files_writer import (
    _render_template,
    format_opm_compact_values,
    round_like_e,
    write_compact_property_file,
    write_grid,
    write_include,
    write_property,
    write_property_inc,
    write_reference_to_coarse_map,
)
from pycopm.utils.input_values import parse_axis_modifications


@dataclass(slots=True)
class CoarseningMaps:
    """Store mappings and intermediate values used during coarsening."""

    #: Axis array marking boundaries removed by coarsening in the x direction.
    #: Values greater than one identify intervals merged with the preceding
    #: interval.
    x: NDArray

    #: Axis array marking boundaries removed by coarsening in the y direction.
    #: Values greater than one identify intervals merged with the preceding
    #: interval.
    y: NDArray

    #: Axis array marking boundaries removed by coarsening in the z direction.
    #: Values greater than one identify intervals merged with the preceding
    #: interval.
    z: NDArray

    #: One-based coarse-cell identifier for each original cell, flattened in
    #: ``(z, y, x)`` order.
    cell_groups: NDArray

    #: Concatenated names of the coarsened axes, for example ``"xz"``.
    coarsened_axes: str

    #: Per-cell mask separating matrix cells (one) from fracture or non-net
    #: cells (zero) in dual-porosity models.
    matrix_mask: NDArray

    #: Whether vertical matrix-fracture transfer connections are retained.
    vertical_transfer_enabled: bool

    #: Coarse-cell identifier for each reference-grid cell, populated while
    #: properties are coarsened.
    reference_to_coarse: list[int] = field(default_factory=list)

    #: NNC include-file content accumulated while mapping non-neighbouring and
    #: matrix-fracture connections.
    nnc_text: str = "NNC\n"

    #: Horizontal x-direction transmissibilities for the matrix or
    #: single-porosity coarse grid.
    coarse_tranx: NDArray = field(default_factory=lambda: np.array([]))

    #: Horizontal y-direction transmissibilities for the matrix or
    #: single-porosity coarse grid.
    coarse_trany: NDArray = field(default_factory=lambda: np.array([]))

    #: Horizontal x-direction transmissibilities for the fracture continuum of
    #: a dual-porosity grid.
    dual_tranx: NDArray = field(default_factory=lambda: np.array([]))

    #: Horizontal y-direction transmissibilities for the fracture continuum of
    #: a dual-porosity grid.
    dual_trany: NDArray = field(default_factory=lambda: np.array([]))

    #: Default property values inserted into separator rows of the extended
    #: dual-porosity grid.
    dual_defaults: dict[str, float] = field(default_factory=dict)


def create_coarsening_maps(
    dck: ConfigViaDeck, cmdargs: argparse.Namespace
) -> CoarseningMaps:
    """Create axis mappings and assign original cells to coarse cells.

    Parameters
    ----------
    dck
        Deck configuration whose output dimensions are updated.
    cmdargs
        Command arguments containing ``coarsening``, ``x_coarsening``,
        ``y_coarsening``, and ``z_coarsening``.

    Returns
    -------
    CoarseningMaps
        Axis mappings, cell groups, and dual-porosity masks."""
    cijk, refs = parse_axis_modifications(
        cmdargs.coarsening,
        [
            cmdargs.x_coarsening,
            cmdargs.y_coarsening,
            cmdargs.z_coarsening,
        ],
    )
    matrix_mask = np.ones(dck.original_porv.size)
    vertical_transfer_enabled = True
    if dck.dual_porosity_criterion:
        dual_criterion = str(dck.dual_porosity_criterion)
        criterion_parts = dual_criterion.split()
        vertical_transfer_enabled = "vertical TF = 0" not in dual_criterion
        property_name = criterion_parts[0].upper()
        comparison_operator = criterion_parts[1]
        comparison_value = float(criterion_parts[2].rstrip(","))
        property_values = np.asarray(dck.init_file[property_name])
        active_cells = dck.original_porv > 0
        if comparison_operator == "==":
            matrix_mask[active_cells] = property_values != comparison_value
        elif comparison_operator == ">=":
            matrix_mask[active_cells] = property_values < comparison_value
        elif comparison_operator == "<=":
            matrix_mask[active_cells] = property_values > comparison_value
        elif comparison_operator == "<":
            matrix_mask[active_cells] = property_values >= comparison_value
        elif comparison_operator == ">":
            matrix_mask[active_cells] = property_values <= comparison_value
        elif comparison_operator == "!=":
            matrix_mask[active_cells] = property_values == comparison_value
        else:
            raise ValueError(f"Unknown criterion for non-net cells: {dual_criterion}")
    directions = ("x", "y", "z")
    original_sizes = (
        dck.original_nx,
        dck.original_ny,
        dck.original_nz,
    )
    if len(cijk) > 2:
        coarsened_axes = "".join(
            direction
            for direction, coarsening_factor in zip(directions, cijk)
            if coarsening_factor > 1
        )
    else:
        coarsened_axes = "".join(
            direction
            for direction_index, direction in enumerate(directions)
            if len(refs[direction_index]) > 0
        )
    coarsenings = []
    for direction_index, original_size in enumerate(original_sizes):
        coarsening_values = np.zeros(original_size + 1, dtype=int)
        if len(cijk) > 2:
            coarsening_values.fill(2)
            coarsening_values[: original_size : cijk[direction_index]] = 0
            coarsening_values[-1] = 0
        elif len(refs[direction_index]) > 0:
            configured_values = np.asarray(
                refs[direction_index],
                dtype=int,
            )
            coarsening_values[: configured_values.size] = configured_values
        coarsenings.append(coarsening_values)
    coarse_coordinates = []
    for coarsening_values, original_size in zip(
        coarsenings,
        original_sizes,
    ):
        coarse_coordinates.append(
            np.concatenate(
                (
                    np.zeros(1, dtype=np.intp),
                    np.cumsum(
                        coarsening_values[1:original_size] <= 1,
                        dtype=np.intp,
                    ),
                )
            )
        )
    coarse_i = coarse_coordinates[0]
    coarse_j = coarse_coordinates[1]
    coarse_k = coarse_coordinates[2]
    coarse_nx = int(coarse_i[-1]) + 1
    coarse_ny = int(coarse_j[-1]) + 1
    cell_groups = (
        coarse_i[None, None, :]
        + coarse_j[None, :, None] * coarse_nx
        + coarse_k[:, None, None] * coarse_nx * coarse_ny
        + 1
    ).reshape(-1)
    for direction, coarsening_values, original_size in zip(
        directions,
        coarsenings,
        original_sizes,
    ):
        setattr(
            dck,
            f"output_n{direction}",
            original_size - int(np.count_nonzero(coarsening_values == 2)),
        )
    return CoarseningMaps(
        x=coarsenings[0],
        y=coarsenings[1],
        z=coarsenings[2],
        cell_groups=cell_groups,
        coarsened_axes=coarsened_axes,
        matrix_mask=matrix_mask,
        vertical_transfer_enabled=vertical_transfer_enabled,
    )


def _grouped_sum(
    values: NDArray,
    groups: NDArray,
    size: int | None = None,
) -> NDArray:
    """Return the sum of values for each one-based group."""
    numeric_values = np.asarray(values, dtype=float)
    group_indices = np.asarray(groups, dtype=int)
    number_groups = int(group_indices.max()) if size is None else size
    valid_values = ~np.isnan(numeric_values)
    return np.bincount(
        group_indices[valid_values] - 1,
        weights=numeric_values[valid_values],
        minlength=number_groups,
    )


def _grouped_count(
    values: NDArray,
    groups: NDArray,
    size: int | None = None,
) -> NDArray:
    """Return the number of non-NaN values for each one-based group."""
    numeric_values = np.asarray(values, dtype=float)
    group_indices = np.asarray(groups, dtype=int)
    number_groups = int(group_indices.max()) if size is None else size
    valid_values = ~np.isnan(numeric_values)
    return np.bincount(
        group_indices[valid_values] - 1,
        minlength=number_groups,
    )


def _grouped_min(
    values: NDArray,
    groups: NDArray,
    size: int | None = None,
) -> NDArray:
    """Return the minimum value for each one-based group, ignoring NaNs."""
    numeric_values = np.asarray(values, dtype=float)
    group_indices = np.asarray(groups, dtype=int)
    number_groups = int(group_indices.max()) if size is None else size
    result = np.full(number_groups, np.inf)
    valid_values = ~np.isnan(numeric_values)
    np.minimum.at(
        result,
        group_indices[valid_values] - 1,
        numeric_values[valid_values],
    )
    result[np.isinf(result)] = np.nan
    return result


def _grouped_max(
    values: NDArray,
    groups: NDArray,
    size: int | None = None,
) -> NDArray:
    """Return the maximum value for each one-based group, ignoring NaNs."""
    numeric_values = np.asarray(values, dtype=float)
    group_indices = np.asarray(groups, dtype=int)
    number_groups = int(group_indices.max()) if size is None else size
    result = np.full(number_groups, -np.inf)
    valid_values = ~np.isnan(numeric_values)
    np.maximum.at(
        result,
        group_indices[valid_values] - 1,
        numeric_values[valid_values],
    )
    result[np.isneginf(result)] = np.nan
    return result


def _grouped_mean(
    values: NDArray,
    groups: NDArray,
    size: int | None = None,
) -> NDArray:
    """Return the mean value for each one-based group, ignoring NaNs."""
    sums = _grouped_sum(values, groups, size)
    counts = _grouped_count(values, groups, size)
    return np.divide(
        sums,
        counts,
        out=np.full(sums.shape, np.nan),
        where=counts > 0,
    )


def _grouped_first(
    values: NDArray,
    groups: NDArray,
    size: int | None = None,
) -> NDArray:
    """Return the first non-NaN value for each one-based group."""
    numeric_values = np.asarray(values, dtype=float)
    group_indices = np.asarray(groups, dtype=int)
    number_groups = int(group_indices.max()) if size is None else size
    source_indices = np.arange(numeric_values.size)
    first_indices = np.full(number_groups, numeric_values.size, dtype=int)
    valid_values = ~np.isnan(numeric_values)
    np.minimum.at(
        first_indices,
        group_indices[valid_values] - 1,
        source_indices[valid_values],
    )
    result = np.full(number_groups, np.nan)
    valid_groups = first_indices < numeric_values.size
    result[valid_groups] = numeric_values[first_indices[valid_groups]]
    return result


def _grouped_last(
    values: NDArray,
    groups: NDArray,
    size: int | None = None,
) -> NDArray:
    """Return the last non-NaN value for each one-based group."""
    numeric_values = np.asarray(values, dtype=float)
    group_indices = np.asarray(groups, dtype=int)
    number_groups = int(group_indices.max()) if size is None else size
    source_indices = np.arange(numeric_values.size)
    last_indices = np.full(number_groups, -1, dtype=int)
    valid_values = ~np.isnan(numeric_values)
    np.maximum.at(
        last_indices,
        group_indices[valid_values] - 1,
        source_indices[valid_values],
    )
    result = np.full(number_groups, np.nan)
    valid_groups = last_indices >= 0
    result[valid_groups] = numeric_values[last_indices[valid_groups]]
    return result


def _grouped_mode(
    values: NDArray,
    group_codes: NDArray,
    number_groups: int,
) -> NDArray:
    """Return the smallest mode for each zero-based group, ignoring NaNs."""
    values = np.asarray(values, dtype=np.float64)
    group_codes = np.asarray(group_codes)
    valid = ~np.isnan(values)
    if not np.any(valid):
        return np.full(number_groups, np.nan, dtype=np.float64)
    valid_groups = group_codes[valid]
    valid_values = values[valid]
    order = np.lexsort((valid_values, valid_groups))
    sorted_groups = valid_groups[order]
    sorted_values = valid_values[order]
    pair_start = np.empty(sorted_values.size, dtype=bool)
    pair_start[0] = True
    pair_start[1:] = (sorted_groups[1:] != sorted_groups[:-1]) | (
        sorted_values[1:] != sorted_values[:-1]
    )
    pair_indices = np.flatnonzero(pair_start)
    pair_groups = sorted_groups[pair_indices]
    pair_values = sorted_values[pair_indices]
    pair_counts = np.diff(np.append(pair_indices, sorted_values.size))
    best_order = np.lexsort(
        (
            pair_values,
            -pair_counts,
            pair_groups,
        )
    )
    candidate_groups = pair_groups[best_order]
    candidate_values = pair_values[best_order]
    first_candidate = np.empty(candidate_groups.size, dtype=bool)
    first_candidate[0] = True
    first_candidate[1:] = candidate_groups[1:] != candidate_groups[:-1]
    result = np.full(number_groups, np.nan, dtype=np.float64)
    result[candidate_groups[first_candidate]] = candidate_values[first_candidate]
    return result


def coarsen_properties(
    dck: ConfigViaDeck,
    coarsening: CoarseningMaps,
    modified_deck: list[str],
    wellcind: list[int],
) -> tuple[NDArray, NDArray, NDArray]:
    """Aggregate reservoir properties onto the coarsened grid.

    Continuous properties use their configured or property-specific aggregation;
    discrete properties use ``min``, ``max``, or ``mode``. The function writes
    property include files and updates output pore volume and active cells.

    Parameters
    ----------
    dck
        Deck configuration and source INIT or restart properties.
    coarsening
        Cell groups and masks created by :func:`create_coarsening_maps`.
    modified_deck
        Deck lines updated with generated property includes.
    wellcind
        Coarse-cell indices containing well completions.

    Returns
    -------
    cluster_minimum, cluster_maximum, removal_mask
        Activity summaries and the mask used to remove depth-jump cells."""
    actnum = np.zeros(dck.original_cell_count, dtype=int)
    top_depths = np.full(dck.original_cell_count, np.nan)
    base_depths = np.full(dck.original_cell_count, np.nan)
    cell_heights = np.full(dck.original_cell_count, np.nan)
    top_corner_indices = (0, 1, 2, 3)
    bottom_corner_indices = (4, 5, 6, 7)
    actnum = (dck.original_porv > 0).astype(int)
    d_x = np.full(dck.original_cell_count, np.nan)
    d_y = np.full(dck.original_cell_count, np.nan)
    d_z = np.full(dck.original_cell_count, np.nan)
    d_ax = np.full(dck.original_cell_count, np.nan)
    d_ay = np.full(dck.original_cell_count, np.nan)
    d_az = np.full(dck.original_cell_count, np.nan)
    permx, permy, permz = np.array([]), np.array([]), np.array([])

    cell_volumes = np.asarray(dck.grid_model.cellvolumes())
    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_ctx = alive_bar(dck.original_cell_count, bar="fish")
    else:
        bar_ctx = nullcontext()
    with bar_ctx as bar_animation:
        for coarse_k in range(dck.original_nz):
            for coarse_j in range(dck.original_ny):
                for coarse_i in range(dck.original_nx):
                    if show_progress:
                        bar_animation()
                    coarsening.reference_to_coarse.append(
                        dck.original_to_output_i[coarse_i + 1]
                        + (dck.original_to_output_j[coarse_j + 1] - 1) * dck.output_nx
                        + (dck.original_to_output_k[coarse_k + 1] - 1)
                        * dck.output_nx
                        * dck.output_ny
                    )
                    coarse_index = (
                        coarse_i
                        + coarse_j * dck.original_nx
                        + coarse_k * dck.original_nx * dck.original_ny
                    )
                    cell_coordinates = dck.grid_model.xyz_from_ijk(
                        coarse_i, coarse_j, coarse_k
                    )
                    x_length_0 = 0.0
                    x_length_1 = 0.0
                    y_length_0 = 0.0
                    y_length_1 = 0.0
                    z_length = 0.0
                    for corner, row_offset, column_offset in zip(
                        range(4), (0, 0, 1, 1), (0, 1, 0, 1)
                    ):
                        x_length_0 += (
                            abs(
                                cell_coordinates[0][1 + 2 * corner]
                                - cell_coordinates[0][2 * corner]
                            )
                            / 4.0
                        )
                        x_length_1 += (
                            abs(
                                cell_coordinates[1][1 + 2 * corner]
                                - cell_coordinates[1][2 * corner]
                            )
                            / 4.0
                        )
                        y_length_0 += (
                            abs(
                                cell_coordinates[0][column_offset + row_offset * 4 + 2]
                                - cell_coordinates[0][column_offset + row_offset * 4]
                            )
                            / 4.0
                        )
                        y_length_1 += (
                            abs(
                                cell_coordinates[1][column_offset + row_offset * 4 + 2]
                                - cell_coordinates[1][column_offset + row_offset * 4]
                            )
                            / 4.0
                        )
                        z_length += (
                            abs(
                                cell_coordinates[2][corner + 4]
                                - cell_coordinates[2][corner]
                            )
                            / 4.0
                        )
                    d_x[coarse_index] = np.hypot(x_length_0, x_length_1)
                    d_y[coarse_index] = np.hypot(y_length_0, y_length_1)
                    d_z[coarse_index] = z_length
                    top_depths[coarse_index] = min(
                        cell_coordinates[2][corner_index]
                        for corner_index in top_corner_indices
                    )
                    base_depths[coarse_index] = max(
                        cell_coordinates[2][corner_index]
                        for corner_index in top_corner_indices
                    )
                    bottom_depth = max(
                        cell_coordinates[2][corner_index]
                        for corner_index in bottom_corner_indices
                    )
                    cell_heights[coarse_index] = bottom_depth - top_depths[coarse_index]

    cluster_ids = np.asarray(coarsening.cell_groups, dtype=int)
    actnum_values = np.asarray(actnum)
    cluster_maximum = _grouped_max(actnum_values, cluster_ids)
    cluster_minimum_all = _grouped_min(actnum_values, cluster_ids)
    group_codes = np.asarray(coarsening.cell_groups, dtype=np.intp) - 1
    number_groups = int(group_codes.max()) + 1
    cluster_mode = _grouped_mode(
        actnum_values,
        group_codes,
        number_groups,
    )
    cluster_frequency = _grouped_sum(actnum_values, cluster_ids)
    mean_cell_height = _grouped_mean(cell_heights, cluster_ids)
    d_ax[dck.original_active_cell_mask] = d_x[dck.original_active_cell_mask]
    d_ay[dck.original_active_cell_mask] = d_y[dck.original_active_cell_mask]
    d_az[dck.original_active_cell_mask] = d_z[dck.original_active_cell_mask]

    x_tot = _grouped_sum(d_x, cluster_ids)
    y_tot = _grouped_sum(d_y, cluster_ids)
    z_tot = _grouped_sum(d_z, cluster_ids)
    za_tot = _grouped_sum(d_az, cluster_ids)
    z_a = _grouped_sum(d_az, cluster_ids)
    if dck.dual_porosity_criterion:
        za_tot = _grouped_sum(d_az * (coarsening.matrix_mask == 1), cluster_ids)
        za_tot_dual = _grouped_sum(d_az * (coarsening.matrix_mask == 0), cluster_ids)

    total_volume = _grouped_sum(cell_volumes, cluster_ids)
    if len(dck.active_cell_methods) == 1:
        if dck.active_cell_methods[0] == "min":
            cluster_minimum = cluster_minimum_all.copy()
        elif dck.active_cell_methods[0] == "mode":
            cluster_minimum = cluster_mode.copy()
        else:
            cluster_minimum = cluster_maximum.copy()
        selected_actnum = cluster_minimum.copy()
    else:
        cluster_minimum = cluster_frequency.copy()
        selected_actnum = cluster_frequency.copy()
        cells_per_coarse_layer = dck.output_nx * dck.output_ny
        for layer_index, aggregation in enumerate(dck.active_cell_methods):
            layer_start = layer_index * cells_per_coarse_layer
            layer_end = min(
                layer_start + cells_per_coarse_layer,
                cluster_frequency.size,
            )
            if aggregation == "min":
                layer_values = cluster_minimum_all[layer_start:layer_end]
            elif aggregation == "mode":
                layer_values = cluster_mode[layer_start:layer_end]
            else:
                layer_values = cluster_maximum[layer_start:layer_end]
            cluster_minimum[layer_start:layer_end] = layer_values
            selected_actnum[layer_start:layer_end] = layer_values
    if dck.jump_thresholds[0]:
        depth_difference = _grouped_max(base_depths, cluster_ids) - _grouped_min(
            top_depths, cluster_ids
        )
        if len(dck.jump_thresholds) == 1:
            removal_mask = (
                depth_difference < float(dck.jump_thresholds[0]) * mean_cell_height
            ).astype(int)
        else:
            removal_mask = np.zeros(cluster_frequency.size)
            cells_per_coarse_layer = dck.output_nx * dck.output_ny
            for layer_index, jump_value in enumerate(dck.jump_thresholds):
                layer_start = layer_index * cells_per_coarse_layer
                layer_end = min(
                    layer_start + cells_per_coarse_layer,
                    cluster_frequency.size,
                )
                removal_mask[layer_start:layer_end] = (
                    depth_difference[layer_start:layer_end]
                    < float(jump_value) * mean_cell_height[layer_start:layer_end]
                )
        dck.output_actnum = (selected_actnum * removal_mask).astype(int)
    else:
        removal_mask = np.ones(mean_cell_height.size)
        dck.output_actnum = selected_actnum.astype(int)
    pore_volume = np.asarray(dck.original_porv, dtype=float)
    if dck.dual_porosity_criterion:
        matrix_pore_volume = _grouped_sum(
            pore_volume * (coarsening.matrix_mask == 1), cluster_ids
        )
        dual_pore_volume = _grouped_sum(
            pore_volume * (coarsening.matrix_mask == 0), cluster_ids
        )
    else:
        matrix_pore_volume = _grouped_sum(pore_volume, cluster_ids)
        dual_pore_volume = np.array([], dtype=float)
    dck.output_porv = matrix_pore_volume

    print("Coarsening continuous quantities (e.g., PORO)")
    number_values = dck.output_nx * dck.output_ny * dck.output_nz
    dual_properties = ("porv", "poro", "tranx", "trany", "tranz")
    zero_dual_properties = ("permx", "permy", "permz")
    transmissibility_properties = {"tranx", "trany", "tranz"}

    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_ctx = alive_bar(len(dck.props_keywords + dck.solution_keywords), bar="fish")
    else:
        bar_ctx = nullcontext()
    with bar_ctx as bar_animation:
        for property_name in dck.props_keywords + dck.solution_keywords:
            if show_progress:
                bar_animation()
            property_values = np.full(dck.original_cell_count, np.nan)
            if property_name in dck.props_keywords:
                property_values[dck.original_active_cell_mask] = dck.init_file[
                    property_name.upper()
                ]
            else:
                property_values[dck.original_active_cell_mask] = dck.restart_file[
                    property_name.upper(), 0
                ]
            aggregation_property_values = property_values.copy()
            use_physical_aggregation = (
                any(not method for method in dck.continuous_aggregation_method)
                or property_name in transmissibility_properties
            )
            if use_physical_aggregation:
                if property_name in ("permx", "permy"):
                    property_values[dck.original_active_cell_mask] *= d_z[
                        dck.original_active_cell_mask
                    ]
                elif property_name == "permz":
                    active_permz = property_values[dck.original_active_cell_mask]
                    property_values[dck.original_active_cell_mask] = np.divide(
                        d_z[dck.original_active_cell_mask],
                        active_permz,
                        out=np.full(active_permz.shape, np.nan),
                        where=active_permz > 0,
                    )
                elif property_name in dck.multipliers_keywords:
                    property_values[dck.original_active_cell_mask] *= total_volume[
                        dck.original_active_cell_mask
                    ]
                elif property_name in transmissibility_properties:
                    direction = property_name[-1]
                    if (
                        len(coarsening.coarsened_axes) == 1
                        and dck.transmissibility_coarsening_method == 1
                        and direction == coarsening.coarsened_axes[0]
                    ):
                        active_transmissibilities = property_values[
                            dck.original_active_cell_mask
                        ]
                        property_values[dck.original_active_cell_mask] = np.divide(
                            1.0,
                            active_transmissibilities,
                            out=np.full(active_transmissibilities.shape, np.nan),
                            where=active_transmissibilities > 0,
                        )
                else:
                    property_values[dck.original_active_cell_mask] *= dck.original_porv[
                        dck.original_active_cell_mask
                    ]
            dual_values = np.array([], dtype=float)
            aggregation_dual_values = np.array([], dtype=float)
            property_dual_c = np.array([], dtype=float)
            if dck.dual_porosity_criterion:
                dual_values = property_values.copy()
                property_values[coarsening.matrix_mask == 0] = 0.0
                dual_values[coarsening.matrix_mask == 1] = 0.0
                aggregation_dual_values = np.where(
                    coarsening.matrix_mask == 0,
                    aggregation_property_values,
                    np.nan,
                )
                aggregation_property_values = np.where(
                    coarsening.matrix_mask == 1,
                    aggregation_property_values,
                    np.nan,
                )
                if property_name in ("tranx", "trany", "tranz"):
                    axis = {"tranx": 2, "trany": 1, "tranz": 0}[property_name]
                    neighboring_mask = np.roll(
                        coarsening.matrix_mask.reshape(
                            dck.original_nz, dck.original_ny, dck.original_nx
                        ),
                        -1,
                        axis=axis,
                    ).ravel()
                    property_values[neighboring_mask == 0] = 0.0
                    dual_values[neighboring_mask == 1] = 0.0
                    aggregation_property_values[neighboring_mask == 0] = np.nan
                    aggregation_dual_values[neighboring_mask == 1] = np.nan
            if use_physical_aggregation:
                grouped_values = _grouped_sum(property_values, cluster_ids)
                grouped_dual_values = (
                    _grouped_sum(dual_values, cluster_ids)
                    if dck.dual_porosity_criterion
                    else np.array([], dtype=float)
                )
                if property_name in ("permx", "permy"):
                    thickness = np.asarray(z_tot, dtype=float)
                    values_c = np.divide(
                        grouped_values,
                        thickness,
                        out=np.zeros(grouped_values.shape),
                        where=(thickness * grouped_values) > 0,
                    )
                    if dck.dual_porosity_criterion:
                        dual_thickness = np.asarray(za_tot_dual, dtype=float)
                        property_dual_c = np.divide(
                            grouped_dual_values,
                            dual_thickness,
                            out=np.zeros(grouped_dual_values.shape),
                            where=(dual_thickness * grouped_dual_values) > 0,
                        )
                elif property_name in ("tranx", "trany"):
                    direction = "x" if property_name == "tranx" else "y"
                    c_tot = x_tot if direction == "x" else y_tot
                    if direction in coarsening.coarsened_axes:
                        if dck.transmissibility_coarsening_method == 1:
                            grouped_minimum = _grouped_min(property_values, cluster_ids)
                            total_length = np.asarray(c_tot, dtype=float)
                            values_c = np.divide(
                                total_length,
                                grouped_values,
                                out=np.zeros(grouped_values.shape),
                                where=(grouped_minimum * grouped_values) > 0,
                            )
                            if dck.dual_porosity_criterion:
                                grouped_dual_minimum = _grouped_min(
                                    dual_values, cluster_ids
                                )
                                property_dual_c = np.divide(
                                    total_length,
                                    grouped_dual_values,
                                    out=np.zeros(grouped_dual_values.shape),
                                    where=(grouped_dual_minimum * grouped_dual_values)
                                    > 0,
                                )
                        else:
                            grouped_average = _grouped_mean(
                                property_values, cluster_ids
                            )
                            grouped_minimum = _grouped_min(property_values, cluster_ids)
                            values_c = np.where(
                                grouped_minimum > 0, grouped_average, 0.0
                            )
                            if dck.dual_porosity_criterion:
                                grouped_dual_average = _grouped_mean(
                                    dual_values, cluster_ids
                                )
                                grouped_dual_minimum = _grouped_min(
                                    dual_values, cluster_ids
                                )
                                property_dual_c = np.where(
                                    grouped_dual_minimum > 0,
                                    grouped_dual_average,
                                    0.0,
                                )
                    else:
                        values_c = np.where(grouped_values > 0, grouped_values, 0.0)
                        if dck.dual_porosity_criterion:
                            property_dual_c = np.where(
                                grouped_dual_values > 0,
                                grouped_dual_values,
                                0.0,
                            )
                elif property_name == "tranz":
                    if "z" in coarsening.coarsened_axes:
                        if dck.transmissibility_coarsening_method == 1:
                            grouped_minimum = _grouped_min(property_values, cluster_ids)
                            average_active_length = _grouped_mean(d_az, cluster_ids)
                            layer_size = dck.output_nx * dck.output_ny
                            if grouped_values.size > layer_size:
                                grouped_values[:-layer_size] = (
                                    (
                                        grouped_values[:-layer_size]
                                        + grouped_values[layer_size:]
                                    )
                                    * (grouped_minimum[:-layer_size] > 0)
                                    * (grouped_minimum[layer_size:] > 0)
                                )
                            total_length = np.asarray(z_tot, dtype=float)
                            denominator = grouped_values * total_length
                            valid_transmissibility = (grouped_values > 0) & (
                                denominator != 0
                            )
                            values_c = np.divide(
                                average_active_length,
                                denominator,
                                out=np.zeros(grouped_values.shape),
                                where=valid_transmissibility,
                            )
                            if dck.dual_porosity_criterion:
                                grouped_dual_minimum = _grouped_min(
                                    dual_values, cluster_ids
                                )
                                average_dual_length = _grouped_mean(
                                    d_az * (coarsening.matrix_mask == 0),
                                    cluster_ids,
                                )
                                if grouped_dual_values.size > layer_size:
                                    grouped_dual_values[:-layer_size] = (
                                        (
                                            grouped_dual_values[:-layer_size]
                                            + grouped_dual_values[layer_size:]
                                        )
                                        * (grouped_dual_minimum[:-layer_size] > 0)
                                        * (grouped_dual_minimum[layer_size:] > 0)
                                    )
                                dual_denominator = grouped_dual_values * total_length
                                valid_dual_transmissibility = (
                                    grouped_dual_values > 0
                                ) & (dual_denominator != 0)
                                property_dual_c = np.divide(
                                    average_dual_length,
                                    dual_denominator,
                                    out=np.zeros(grouped_dual_values.shape),
                                    where=valid_dual_transmissibility,
                                )
                        else:
                            last_transmissibility = _grouped_last(
                                property_values, cluster_ids
                            )
                            last_cell_volume = _grouped_last(cell_volumes, cluster_ids)
                            first_cell_volume = _grouped_first(
                                cell_volumes, cluster_ids
                            )
                            layer_size = dck.original_nx * dck.original_ny
                            shifted_first_volume = np.roll(
                                first_cell_volume, -layer_size
                            )
                            shifted_total_volume = np.roll(total_volume, -layer_size)
                            numerator = last_transmissibility * (
                                last_cell_volume + shifted_first_volume
                            )
                            denominator = total_volume + shifted_total_volume
                            values_c = np.divide(
                                numerator,
                                denominator,
                                out=np.zeros(last_transmissibility.shape),
                                where=(last_transmissibility > 0) & (denominator != 0),
                            )
                            if dck.dual_porosity_criterion:
                                last_dual_transmissibility = _grouped_last(
                                    dual_values, cluster_ids
                                )
                                dual_numerator = last_dual_transmissibility * (
                                    last_cell_volume + shifted_first_volume
                                )
                                property_dual_c = np.divide(
                                    dual_numerator,
                                    denominator,
                                    out=np.zeros(last_dual_transmissibility.shape),
                                    where=(last_dual_transmissibility > 0)
                                    & (denominator != 0),
                                )
                    else:
                        active_length = np.asarray(z_a, dtype=float)
                        total_length = np.asarray(z_tot, dtype=float)
                        valid_transmissibility = (grouped_values > 0) & (
                            total_length != 0
                        )
                        values_c = np.divide(
                            grouped_values * active_length,
                            total_length,
                            out=np.zeros(grouped_values.shape),
                            where=valid_transmissibility,
                        )
                        if dck.dual_porosity_criterion:
                            dual_active_length = np.asarray(za_tot_dual, dtype=float)
                            valid_dual_transmissibility = (grouped_dual_values > 0) & (
                                total_length != 0
                            )
                            property_dual_c = np.divide(
                                grouped_dual_values * dual_active_length,
                                total_length,
                                out=np.zeros(grouped_dual_values.shape),
                                where=valid_dual_transmissibility,
                            )
                elif property_name == "permz":
                    thickness = np.asarray(za_tot, dtype=float)
                    values_c = np.divide(
                        thickness,
                        grouped_values,
                        out=np.zeros(grouped_values.shape),
                        where=(thickness * grouped_values) > 0,
                    )
                    if dck.dual_porosity_criterion:
                        dual_thickness = np.asarray(za_tot_dual, dtype=float)
                        property_dual_c = np.divide(
                            dual_thickness,
                            grouped_dual_values,
                            out=np.zeros(grouped_dual_values.shape),
                            where=(dual_thickness * grouped_dual_values) > 0,
                        )
                elif property_name in (
                    "poro",
                    "swatinit",
                    "disperc",
                    "thconr",
                    *dck.solution_keywords,
                ):
                    values_c = np.divide(
                        grouped_values,
                        matrix_pore_volume,
                        out=np.zeros(grouped_values.shape),
                        where=matrix_pore_volume > 0,
                    )
                    if dck.dual_porosity_criterion and property_name == "poro":
                        property_dual_c = np.divide(
                            grouped_dual_values,
                            dual_pore_volume,
                            out=np.zeros(grouped_dual_values.shape),
                            where=dual_pore_volume > 0,
                        )
                else:
                    values_c = np.divide(
                        grouped_values,
                        total_volume,
                        out=np.zeros(grouped_values.shape),
                        where=total_volume > 0,
                    )
            elif len(dck.continuous_aggregation_method) == 1:
                aggregation = dck.continuous_aggregation_method[0]
                if aggregation == "min":
                    values_c = _grouped_min(aggregation_property_values, cluster_ids)
                    if dck.dual_porosity_criterion:
                        property_dual_c = _grouped_min(
                            aggregation_dual_values, cluster_ids
                        )
                elif aggregation == "max":
                    values_c = _grouped_max(aggregation_property_values, cluster_ids)
                    if dck.dual_porosity_criterion:
                        property_dual_c = _grouped_max(
                            aggregation_dual_values, cluster_ids
                        )
                elif aggregation == "pvmean":
                    pv_property_values = aggregation_property_values * dck.original_porv
                    grouped_values = _grouped_sum(pv_property_values, cluster_ids)
                    values_c = np.divide(
                        grouped_values,
                        matrix_pore_volume,
                        out=np.zeros(grouped_values.shape),
                        where=matrix_pore_volume > 0,
                    )
                    if dck.dual_porosity_criterion:
                        pv_dual_values = aggregation_dual_values * dck.original_porv
                        grouped_dual_values = _grouped_sum(pv_dual_values, cluster_ids)
                        property_dual_c = np.divide(
                            grouped_dual_values,
                            dual_pore_volume,
                            out=np.zeros(grouped_dual_values.shape),
                            where=dual_pore_volume > 0,
                        )
                else:
                    values_c = _grouped_mean(aggregation_property_values, cluster_ids)
                    if dck.dual_porosity_criterion:
                        property_dual_c = _grouped_mean(
                            aggregation_dual_values, cluster_ids
                        )
            else:
                grouped_minimum = _grouped_min(aggregation_property_values, cluster_ids)
                grouped_maximum = _grouped_max(aggregation_property_values, cluster_ids)
                grouped_mean = _grouped_mean(aggregation_property_values, cluster_ids)
                pv_property_values = aggregation_property_values * dck.original_porv
                grouped_pv_values = _grouped_sum(pv_property_values, cluster_ids)
                grouped_pvmean = np.divide(
                    grouped_pv_values,
                    matrix_pore_volume,
                    out=np.zeros(grouped_pv_values.shape),
                    where=matrix_pore_volume > 0,
                )
                values_c = grouped_mean.copy()
                if dck.dual_porosity_criterion:
                    grouped_dual_minimum = _grouped_min(
                        aggregation_dual_values, cluster_ids
                    )
                    grouped_dual_maximum = _grouped_max(
                        aggregation_dual_values, cluster_ids
                    )
                    grouped_dual_mean = _grouped_mean(
                        aggregation_dual_values, cluster_ids
                    )
                    pv_dual_values = aggregation_dual_values * dck.original_porv
                    grouped_dual_pv_values = _grouped_sum(pv_dual_values, cluster_ids)
                    grouped_dual_pvmean = np.divide(
                        grouped_dual_pv_values,
                        dual_pore_volume,
                        out=np.zeros(grouped_dual_pv_values.shape),
                        where=dual_pore_volume > 0,
                    )
                    property_dual_c = grouped_dual_mean.copy()
                cells_per_coarse_layer = dck.output_nx * dck.output_ny
                for layer_index, aggregation in enumerate(
                    dck.continuous_aggregation_method
                ):
                    layer_start = layer_index * cells_per_coarse_layer
                    layer_end = min(
                        layer_start + cells_per_coarse_layer,
                        values_c.size,
                    )
                    if aggregation == "min":
                        values_c[layer_start:layer_end] = grouped_minimum[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = (
                                grouped_dual_minimum[layer_start:layer_end]
                            )
                    elif aggregation == "max":
                        values_c[layer_start:layer_end] = grouped_maximum[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = (
                                grouped_dual_maximum[layer_start:layer_end]
                            )
                    elif aggregation == "pvmean":
                        values_c[layer_start:layer_end] = grouped_pvmean[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = (
                                grouped_dual_pvmean[layer_start:layer_end]
                            )
                    else:
                        values_c[layer_start:layer_end] = grouped_mean[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = grouped_dual_mean[
                                layer_start:layer_end
                            ]
            if (
                len(dck.continuous_aggregation_method) > 1
                and use_physical_aggregation
                and property_name not in transmissibility_properties
            ):
                grouped_minimum = _grouped_min(aggregation_property_values, cluster_ids)
                grouped_maximum = _grouped_max(aggregation_property_values, cluster_ids)
                grouped_mean = _grouped_mean(aggregation_property_values, cluster_ids)
                pv_property_values = aggregation_property_values * dck.original_porv
                grouped_pv_values = _grouped_sum(pv_property_values, cluster_ids)
                grouped_pvmean = np.divide(
                    grouped_pv_values,
                    matrix_pore_volume,
                    out=np.zeros(grouped_pv_values.shape),
                    where=matrix_pore_volume > 0,
                )
                if dck.dual_porosity_criterion:
                    grouped_dual_minimum = _grouped_min(
                        aggregation_dual_values, cluster_ids
                    )
                    grouped_dual_maximum = _grouped_max(
                        aggregation_dual_values, cluster_ids
                    )
                    grouped_dual_mean = _grouped_mean(
                        aggregation_dual_values, cluster_ids
                    )
                    pv_dual_values = aggregation_dual_values * dck.original_porv
                    grouped_dual_pv_values = _grouped_sum(pv_dual_values, cluster_ids)
                    grouped_dual_pvmean = np.divide(
                        grouped_dual_pv_values,
                        dual_pore_volume,
                        out=np.zeros(grouped_dual_pv_values.shape),
                        where=dual_pore_volume > 0,
                    )
                cells_per_coarse_layer = dck.output_nx * dck.output_ny
                for layer_index, aggregation in enumerate(
                    dck.continuous_aggregation_method
                ):
                    layer_start = layer_index * cells_per_coarse_layer
                    layer_end = min(
                        layer_start + cells_per_coarse_layer,
                        values_c.size,
                    )
                    if aggregation == "min":
                        values_c[layer_start:layer_end] = grouped_minimum[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = (
                                grouped_dual_minimum[layer_start:layer_end]
                            )
                    elif aggregation == "max":
                        values_c[layer_start:layer_end] = grouped_maximum[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = (
                                grouped_dual_maximum[layer_start:layer_end]
                            )
                    elif aggregation == "pvmean":
                        values_c[layer_start:layer_end] = grouped_pvmean[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = (
                                grouped_dual_pvmean[layer_start:layer_end]
                            )
                    elif aggregation:
                        values_c[layer_start:layer_end] = grouped_mean[
                            layer_start:layer_end
                        ]
                        if dck.dual_porosity_criterion:
                            property_dual_c[layer_start:layer_end] = grouped_dual_mean[
                                layer_start:layer_end
                            ]
            values_c = np.asarray(values_c, dtype=float)
            values_c[np.isnan(values_c)] = 0.0
            if property_dual_c.size:
                property_dual_c = np.asarray(property_dual_c, dtype=float)
                property_dual_c[np.isnan(property_dual_c)] = 0.0
            if (
                dck.coarsening_enabled
                and dck.transmissibility_coarsening_method > 0
                and property_name in ["permx", "permy", "permz"]
            ):
                well_indices = np.asarray(wellcind, dtype=int)
                property_values = np.asarray(values_c)
                keep_values = np.zeros(property_values.size, dtype=bool)
                keep_values[well_indices] = True
                values_c = np.where(keep_values, property_values, 0.0)
            if property_name == "tranx":
                coarsening.coarse_tranx = values_c
                if dck.dual_porosity_criterion:
                    coarsening.dual_tranx = property_dual_c
            elif property_name == "trany":
                coarsening.coarse_trany = values_c
                if dck.dual_porosity_criterion:
                    coarsening.dual_trany = property_dual_c
            if property_name == "permx":
                permx = values_c
            if property_name == "permy":
                permy = values_c
            if property_name == "permz":
                permz = values_c
            property_values = np.asarray(values_c)
            allow_inline = not dck.dual_porosity_criterion and not (
                dck.transmissibility_coarsening_method > 0
                and property_name
                in (
                    "tranx",
                    "trany",
                    "tranz",
                    "permy",
                    "permz",
                )
            )
            property_inlined = write_property_inc(
                dck,
                property_name,
                values_c,
                number_values,
                modified_deck,
                allow_inline,
            )
            if property_inlined:
                continue
            if dck.dual_porosity_criterion and property_name in [
                "poro",
                "tranz",
                "permx",
                "permy",
                "permz",
            ]:
                if property_name in dual_properties:
                    dual_values_c = np.asarray(property_dual_c)
                elif property_name in zero_dual_properties:
                    dual_values_c = np.zeros_like(property_values)
                else:
                    dual_values_c = property_values
                property_values = _interleave_dual_property(
                    property_values,
                    dual_values_c,
                    dck.output_nx,
                    dck.output_nz,
                )
                write_property_inc(
                    dck,
                    property_name,
                    property_values,
                    property_values.size,
                    modified_deck,
                    False,
                    "_DUAL_TMP_PYCOPM",
                )
    if dck.dual_porosity_criterion:
        property_values = np.asarray(dck.output_porv)
        property_name = "porv"
        property_values = _interleave_dual_property(
            property_values,
            dual_pore_volume,
            dck.output_nx,
            dck.output_nz,
        )
        write_property_inc(
            dck,
            property_name,
            property_values,
            property_values.size,
            modified_deck,
            False,
            "_DUAL_TMP_PYCOPM",
        )
    _compact_permeability_properties(dck, permx, permy, permz, modified_deck)
    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_ctx = alive_bar(len(dck.regions_keywords + dck.grids_keywords), bar="fish")
    else:
        bar_ctx = nullcontext()
    print("Coarsening discrete quantities (e.g., SATNUM)")
    with bar_ctx as bar_animation:
        for property_name in dck.regions_keywords + dck.grids_keywords:
            if show_progress:
                bar_animation()
            values = np.full(dck.original_cell_count, np.nan)
            values[dck.original_active_cell_mask] = dck.init_file[property_name.upper()]
            property_values = np.asarray(values, dtype=float)
            valid_property_values = property_values[~np.isnan(property_values)]
            default_value = 0.0
            if valid_property_values.size == 0:
                grouped_values = np.full(int(cluster_ids.max()), np.nan)
            elif np.max(valid_property_values) == np.min(valid_property_values):
                default_value = float(valid_property_values[0])
                coarsening.dual_defaults[property_name] = default_value
                grouped_values = _grouped_min(property_values, cluster_ids)
            elif len(dck.discrete_aggregation_method) == 1:
                aggregation = dck.discrete_aggregation_method[0]
                if aggregation == "min":
                    grouped_values = _grouped_min(property_values, cluster_ids)
                elif aggregation == "max":
                    grouped_values = _grouped_max(property_values, cluster_ids)
                else:
                    group_codes = np.asarray(coarsening.cell_groups, dtype=np.intp) - 1
                    number_groups = int(group_codes.max()) + 1
                    grouped_values = _grouped_mode(
                        property_values,
                        group_codes,
                        number_groups,
                    )
            else:
                grouped_minimum = _grouped_min(property_values, cluster_ids)
                grouped_maximum = _grouped_max(property_values, cluster_ids)
                group_codes = np.asarray(coarsening.cell_groups, dtype=np.intp) - 1
                number_groups = int(group_codes.max()) + 1
                grouped_mode = _grouped_mode(
                    property_values,
                    group_codes,
                    number_groups,
                )
                grouped_values = grouped_mode.copy()
                cells_per_coarse_layer = dck.output_nx * dck.output_ny
                for layer_index, aggregation in enumerate(
                    dck.discrete_aggregation_method
                ):
                    layer_start = layer_index * cells_per_coarse_layer
                    layer_end = min(
                        layer_start + cells_per_coarse_layer,
                        grouped_values.size,
                    )
                    if aggregation == "min":
                        layer_values = grouped_minimum[layer_start:layer_end]
                    elif aggregation == "max":
                        layer_values = grouped_maximum[layer_start:layer_end]
                    else:
                        layer_values = grouped_mode[layer_start:layer_end]
                    grouped_values[layer_start:layer_end] = layer_values
            values_c = np.where(
                np.isnan(grouped_values), default_value, grouped_values
            ).astype(int)
            property_inlined = write_property_inc(
                dck,
                property_name,
                values_c,
                number_values,
                modified_deck,
                not dck.dual_porosity_criterion,
            )
            if property_inlined:
                continue
            if dck.dual_porosity_criterion:
                default_value = coarsening.dual_defaults.get(property_name, 0)
                if property_name == "fluxnum":
                    matrix_values = np.ones_like(values_c)
                    dual_values = np.full_like(values_c, 2)
                else:
                    matrix_values = np.asarray(values_c)
                    dual_values = matrix_values
                property_values = _interleave_dual_property(
                    matrix_values,
                    dual_values,
                    dck.output_nx,
                    dck.output_nz,
                    default_value,
                )
                write_property_inc(
                    dck,
                    property_name,
                    property_values,
                    property_values.size,
                    modified_deck,
                    False,
                    "_DUAL_TMP_PYCOPM",
                )

    write_reference_to_coarse_map(dck, np.array(coarsening.reference_to_coarse))

    return cluster_minimum, cluster_maximum, removal_mask


def _interleave_dual_property(
    property_values: NDArray,
    dual_values: NDArray,
    nx: int,
    nz: int,
    default_value: float = 0,
) -> NDArray:
    """Interleave property and dual-property layers with separator rows."""
    property_values = np.asarray(property_values)
    dual_values = np.asarray(dual_values)
    cells_per_layer = property_values.size // nz
    output_dtype = np.result_type(
        property_values.dtype,
        dual_values.dtype,
        np.asarray(default_value).dtype,
    )
    property_values = property_values.astype(output_dtype, copy=False)
    dual_values = dual_values.astype(output_dtype, copy=False)
    separator_values = np.full(
        nx,
        default_value,
        dtype=output_dtype,
    )
    property_blocks: list[NDArray] = []
    for layer_index in range(nz):
        layer_slice = slice(
            layer_index * cells_per_layer,
            (layer_index + 1) * cells_per_layer,
        )
        property_blocks.append(property_values[layer_slice])
        property_blocks.append(separator_values)
        property_blocks.append(dual_values[layer_slice])
    return np.concatenate(property_blocks)


def _find_include_statement(
    modified_deck: list[str],
    include_line: str,
) -> tuple[int, int]:
    """Return the list interval containing an INCLUDE statement."""
    include_index = modified_deck.index(include_line)
    start_index = include_index
    for index in range(include_index - 1, -1, -1):
        line = modified_deck[index]
        code = line.split("--", maxsplit=1)[0]
        if not code.strip():
            continue
        if re.fullmatch(r"\s*INCLUDE\s*", code, flags=re.IGNORECASE):
            start_index = index
        break
    return start_index, include_index + 1


def _compact_permeability_properties(
    dck: ConfigViaDeck,
    permx: NDArray,
    permy: NDArray,
    permz: NDArray,
    modified_deck: list[str],
) -> None:
    """Use COPY and MULTIPLY if PERMY and PERMZ can be generated from PERMX."""
    copy_permy = np.array_equal(permx, permy)
    copy_permz = False
    output_path = Path(dck.output_directory)
    permx_values = np.asarray(dck.init_file["PERMX"])
    permz_values = np.asarray(dck.init_file["PERMZ"])
    valid_permeability = (permx_values != 0) & (permz_values != 0)
    facpermz = -1.0
    if np.any(valid_permeability):
        first_valid_index = int(np.flatnonzero(valid_permeability)[0])
        facpermz = float(
            permz_values[first_valid_index] / permx_values[first_valid_index]
        )
    if facpermz > 0 and np.all(np.abs(permz - facpermz * permx) <= 1e-12):
        copy_permz = True
    include_statements = []
    if copy_permy:
        include_line = f"'{dck.include_prefix}PERMY.INC' /\n"
        include_statements.append(_find_include_statement(modified_deck, include_line))
    if copy_permz:
        include_line = f"'{dck.include_prefix}PERMZ.INC' /\n"
        include_statements.append(_find_include_statement(modified_deck, include_line))
    if not include_statements:
        return
    insertion_index = min(start_index for start_index, _ in include_statements)
    for start_index, end_index in sorted(include_statements, reverse=True):
        del modified_deck[start_index:end_index]
    if copy_permy and copy_permz:
        text = "COPY\nPERMX PERMY /\nPERMX PERMZ /\n/\n"
        if abs(1 - facpermz) > 1e-12:
            text += f"\nMULTIPLY\nPERMZ {facpermz:.4E} /\n/\n"
        modified_deck.insert(insertion_index, text)
    elif copy_permy:
        modified_deck.insert(
            insertion_index,
            "COPY\nPERMX PERMY /\n/\n",
        )
    elif copy_permz:
        text = "COPY\nPERMX PERMZ /\n/"
        if abs(1 - facpermz) > 1e-12:
            text += f"\nMULTIPLY\nPERMZ {facpermz:.4E} /\n/\n"
        modified_deck.insert(insertion_index, text)
    if copy_permy:
        permy_path = output_path / f"{dck.include_prefix}PERMY.INC"
        permy_path.unlink(missing_ok=True)
        permy_path = output_path / f"{dck.include_prefix}PERMY_DUAL_TMP_PYCOPM.INC"
        permy_path.unlink(missing_ok=True)
    if copy_permz:
        permz_path = output_path / f"{dck.include_prefix}PERMZ.INC"
        permz_path.unlink(missing_ok=True)
        permz_path = output_path / f"{dck.include_prefix}PERMZ_DUAL_TMP_PYCOPM.INC"
        permz_path.unlink(missing_ok=True)


def redistribute_removed_pore_volume(
    dck: ConfigViaDeck,
    con: NDArray,
    cluster_minimum: NDArray,
    cluster_maximum: NDArray,
    removal_mask: NDArray,
) -> None:
    """Redistribute pore volume from removed coarse cells.

    Pore volume is divided among the nearest active neighbours without changing
    the total pore volume.

    Parameters
    ----------
    dck
        Deck configuration whose ``output_porv`` is updated.
    con
        One-based coarse-cell identifier for each original cell.
    cluster_minimum, cluster_maximum
        Aggregated activity values used to identify changed clusters.
    removal_mask
        Mask identifying retained coarse cells."""
    cluster_ids = np.asarray(con, dtype=int)
    pore_volumes = np.asarray(dck.original_porv, dtype=float)
    dck.output_porv = np.asarray(dck.output_porv, dtype=float)
    grouped_pore_volume = np.bincount(
        cluster_ids,
        weights=pore_volumes,
        minlength=int(np.max(cluster_ids)) + 1,
    )
    cluster_minimum = np.asarray(cluster_minimum)
    cluster_maximum = np.asarray(cluster_maximum)
    removal_mask = np.asarray(removal_mask)
    changed_clusters = np.flatnonzero(cluster_maximum - cluster_minimum > 0) + 1
    removed_clusters = np.flatnonzero(removal_mask == 0) + 1
    redistribution_clusters = np.union1d(changed_clusters, removed_clusters)
    maximum_distance = max(dck.output_nx, dck.output_ny, dck.output_nz)
    total_cells = dck.output_nx * dck.output_ny * dck.output_nz
    for cluster_value in redistribution_clusters:
        cluster_id = int(cluster_value)
        i, j, k = _global_index_to_ijk(dck, cluster_id - 1)
        neighbor_indices: list[int] = []
        distance = 0
        offset = 0
        while not neighbor_indices and offset < total_cells:
            neighbor_indices = _find_active_neighbors(
                dck,
                neighbor_indices,
                cluster_id,
                distance,
                offset,
                [i, j, k],
            )
            distance += 1
            if distance > maximum_distance:
                distance = 0
                offset += 1
        if not neighbor_indices:
            raise ValueError(
                "No active cell found to receive pore volume from "
                f"cluster {cluster_id}"
            )
        pore_volume_increment = grouped_pore_volume[cluster_id] / len(neighbor_indices)
        dck.output_porv[
            np.asarray(neighbor_indices, dtype=int)
        ] += pore_volume_increment


def _find_active_neighbors(
    dck: ConfigViaDeck,
    neighbor_indices: list[int],
    cluster_id: int,
    distance: int,
    offset: int,
    ijk: list,
) -> list[int]:
    """Find active neighbouring cells for pore-volume redistribution."""
    total_cells = dck.output_nx * dck.output_ny * dck.output_nz
    candidates = (
        (ijk[0] + 1 + distance < dck.output_nx, cluster_id + distance + offset),
        (ijk[0] - 1 - distance >= 0, cluster_id - 2 - distance + offset),
        (
            ijk[1] + 1 + distance < dck.output_ny,
            cluster_id - 1 + (distance + 1) * dck.output_nx + offset,
        ),
        (
            ijk[1] - 1 - distance >= 0,
            cluster_id - 1 - (distance + 1) * dck.output_nx + offset,
        ),
        (
            ijk[2] + 1 + distance < dck.output_nz,
            cluster_id - 1 + (distance + 1) * dck.output_nx * dck.output_ny + offset,
        ),
        (
            ijk[2] - 1 - distance >= 0,
            cluster_id - 1 - (distance + 1) * dck.output_nx * dck.output_ny + offset,
        ),
    )
    for valid_direction, candidate_index in candidates:
        if (
            valid_direction
            and 0 <= candidate_index < total_cells
            and dck.output_actnum[candidate_index] == 1
        ):
            neighbor_indices.append(candidate_index)
    return neighbor_indices


def _global_index_to_ijk(dck: ConfigViaDeck, global_index: int) -> tuple[int, int, int]:
    """Return the i, j, and k indices from a zero-based global cell index."""
    cells_per_layer = dck.output_nx * dck.output_ny
    k_index, layer_index = divmod(global_index, cells_per_layer)
    j_index, i_index = divmod(layer_index, dck.output_nx)
    return i_index, j_index, k_index


def coarsen_corner_point_grid(
    dck: ConfigViaDeck, coarsening: CoarseningMaps
) -> tuple[NDArray, NDArray]:
    """Remove selected pillars and ZCORN surfaces from the grid.

    Parameters
    ----------
    dck
        Deck configuration containing the original corner-point grid.
    coarsening
        Axis mappings defining the removed rows, columns, and layers.

    Returns
    -------
    coord, zcorn
        Coarsened arrays when dual porosity is enabled; otherwise empty arrays."""
    original_nx = dck.original_nx
    original_ny = dck.original_ny
    original_nz = dck.original_nz
    pillars_per_row = original_nx + 1
    pillar_count = pillars_per_row * (original_ny + 1)
    cells_per_layer = original_nx * original_ny
    total_zcorn_values = 8 * cells_per_layer * original_nz
    coord_values = np.asarray(dck.egrid_file["COORD"]).reshape(-1)
    zcorn_values = np.asarray(dck.egrid_file["ZCORN"]).reshape(-1)
    removed_columns = np.flatnonzero(np.asarray(coarsening.x) > 1)
    removed_rows = np.flatnonzero(np.asarray(coarsening.y) > 1)
    removed_pillar_mask = np.zeros(
        (original_ny + 1, pillars_per_row),
        dtype=bool,
    )
    removed_pillar_mask[:, removed_columns] = True
    removed_pillar_mask[removed_rows, :] = True
    coord_matrix = coord_values.reshape(pillar_count, 6)
    coarsened_coord_values = coord_matrix[~removed_pillar_mask.ravel()].reshape(-1)
    zcorn_removal_mask = np.zeros(total_zcorn_values, dtype=bool)
    column_offsets = np.arange(2, dtype=np.intp)
    row_offsets = np.arange(4 * original_nx, dtype=np.intp)
    for column_index in removed_columns:
        column_starts = np.arange(
            2 * column_index - 1,
            total_zcorn_values,
            2 * original_nx,
            dtype=np.intp,
        )
        column_indices = (column_starts[:, None] + column_offsets).reshape(-1)
        zcorn_removal_mask[column_indices] = True
    for row_index in removed_rows:
        row_starts = np.arange(
            (2 * row_index - 1) * 2 * original_nx,
            total_zcorn_values,
            4 * cells_per_layer,
            dtype=np.intp,
        )
        row_indices = (row_starts[:, None] + row_offsets).reshape(-1)
        zcorn_removal_mask[row_indices] = True
    zcorn_removal_indices = np.flatnonzero(zcorn_removal_mask).tolist()
    zcorn_removal_indices = _collect_removed_zcorn_indices(
        dck,
        coarsening.z,
        zcorn_removal_indices,
    )
    final_zcorn_removal_indices = np.asarray(
        zcorn_removal_indices,
        dtype=np.intp,
    )
    zcorn_removal_mask.fill(False)
    if final_zcorn_removal_indices.size:
        zcorn_removal_mask[final_zcorn_removal_indices] = True
    coarsened_zcorn_values = zcorn_values[~zcorn_removal_mask]
    write_grid(
        dck,
        coarsened_coord_values,
        coarsened_zcorn_values,
        False,
    )
    if dck.dual_porosity_criterion:
        return coarsened_coord_values, coarsened_zcorn_values
    return np.array([]), np.array([])


def build_dual_porosity_grid(
    dck: ConfigViaDeck, coarsening: CoarseningMaps, cr: NDArray, zc: NDArray
) -> tuple[NDArray, NDArray]:
    """Extend a coarsened grid with a second porosity continuum.

    The matrix and fracture grids are separated in the j direction, and their
    connections are added to ``coarsening.nnc_text``.

    Parameters
    ----------
    dck
        Deck configuration for the coarsened model.
    coarsening
        Coarsening data containing continuum masks and transmissibilities.
    cr, zc
        Coarsened ``COORD`` and ``ZCORN`` arrays.

    Returns
    -------
    coord, zcorn
        Extended dual-porosity grid arrays."""
    num_dig = dck.significant_digits
    cells_per_layer = dck.output_nx * dck.output_ny
    coord_values = np.asarray(cr, dtype=float)
    y_offset = 1.075 * max(
        coord_values[-6 * (dck.output_nx + 1) + 1] - coord_values[1],
        coord_values[-2] - coord_values[6 * (dck.output_nx + 1) - 2],
    )
    shifted_coord = coord_values.copy()
    shifted_coord[1::3] += y_offset
    cr = np.concatenate((coord_values, shifted_coord))
    zcorn_values = np.asarray(zc, dtype=float)
    values_per_surface = 4 * cells_per_layer
    zcorn_blocks: list[NDArray] = []
    for surface_index in range(zcorn_values.size // values_per_surface):
        surface_start = surface_index * values_per_surface
        surface_end = surface_start + values_per_surface
        surface_values = zcorn_values[surface_start:surface_end]
        zcorn_blocks.extend(
            (
                surface_values,
                surface_values[-2 * dck.output_nx :],
                surface_values[: 2 * dck.output_nx],
                surface_values,
            )
        )
    zc = np.concatenate(zcorn_blocks)
    mask_values = np.asarray(coarsening.matrix_mask)
    values = np.full(dck.original_cell_count, np.nan)
    values[dck.original_active_cell_mask] = dck.init_file["TRANX"]
    tranx_values = np.asarray(values, dtype=float)
    values = np.full(dck.original_cell_count, np.nan)
    values[dck.original_active_cell_mask] = dck.init_file["TRANY"]
    trany_values = np.asarray(values, dtype=float)
    values = np.full(dck.original_cell_count, np.nan)
    values[dck.original_active_cell_mask] = dck.init_file["TRANZ"]
    tranz_values = np.asarray(values, dtype=float)
    porv_values = np.asarray(dck.output_porv, dtype=float)
    cluster_ids = np.asarray(coarsening.cell_groups, dtype=int)
    dual_porv_values = _grouped_sum(
        dck.original_porv * (coarsening.matrix_mask == 0), cluster_ids
    )
    nnc_lines: list[str] = []
    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_ctx = alive_bar(cells_per_layer * dck.output_nz, bar="fish")
    else:
        bar_ctx = nullcontext()
    print("Handling the dual connectivity")
    with bar_ctx as bar_animation:
        for row_index in range(dck.original_ny):
            for column_index in range(dck.original_nx):
                original_layer = 0
                for layer_index in range(dck.output_nz):
                    if show_progress:
                        bar_animation()
                    positive_x = 0.0
                    negative_x = 0.0
                    positive_y = 0.0
                    negative_y = 0.0
                    vertical = 0.0
                    while (
                        original_layer + 1 < len(coarsening.z)
                        and coarsening.z[original_layer + 1] == 2
                    ):
                        original_index = (
                            column_index
                            + row_index * dck.original_nx
                            + original_layer * cells_per_layer
                        )
                        coarse_index = (
                            column_index
                            + row_index * dck.original_nx
                            + layer_index * cells_per_layer
                        )
                        if (
                            original_index + cells_per_layer < mask_values.size
                            and mask_values[original_index]
                            != mask_values[original_index + cells_per_layer]
                            and dual_porv_values[coarse_index] > 0
                            and porv_values[coarse_index] > 0
                            and not np.isnan(tranz_values[original_index])
                            and coarsening.vertical_transfer_enabled
                        ):
                            vertical += tranz_values[original_index]
                        if (
                            column_index < dck.original_nx - 1
                            and mask_values[original_index] == 1
                            and mask_values[original_index + 1] == 0
                            and dual_porv_values[coarse_index + 1] > 0
                            and not np.isnan(tranx_values[original_index])
                        ):
                            positive_x += tranx_values[original_index]
                        if (
                            column_index > 0
                            and mask_values[original_index - 1] == 0
                            and mask_values[original_index] == 1
                            and dual_porv_values[coarse_index - 1] > 0
                            and not np.isnan(tranx_values[original_index - 1])
                        ):
                            negative_x += tranx_values[original_index - 1]
                        if (
                            row_index < dck.original_ny - 1
                            and mask_values[original_index] == 1
                            and mask_values[original_index + dck.original_nx] == 0
                            and dual_porv_values[coarse_index + dck.original_nx] > 0
                            and not np.isnan(trany_values[original_index])
                        ):
                            positive_y += trany_values[original_index]
                        if (
                            row_index > 0
                            and mask_values[original_index - dck.original_nx] == 0
                            and mask_values[original_index] == 1
                            and dual_porv_values[coarse_index - dck.original_nx] > 0
                            and not np.isnan(
                                trany_values[original_index - dck.original_nx]
                            )
                        ):
                            negative_y += trany_values[original_index - dck.original_nx]
                        original_layer += 1
                    original_index = (
                        column_index
                        + row_index * dck.original_nx
                        + original_layer * cells_per_layer
                    )
                    coarse_index = (
                        column_index
                        + row_index * dck.original_nx
                        + layer_index * cells_per_layer
                    )
                    if (
                        column_index < dck.original_nx - 1
                        and mask_values[original_index] == 1
                        and mask_values[original_index + 1] == 0
                        and dual_porv_values[coarse_index + 1] > 0
                        and not np.isnan(tranx_values[original_index])
                    ):
                        positive_x += tranx_values[original_index]
                    if (
                        column_index > 0
                        and mask_values[original_index - 1] == 0
                        and mask_values[original_index] == 1
                        and dual_porv_values[coarse_index - 1] > 0
                        and not np.isnan(tranx_values[original_index - 1])
                    ):
                        negative_x += tranx_values[original_index - 1]
                    if (
                        row_index < dck.original_ny - 1
                        and mask_values[original_index] == 1
                        and mask_values[original_index + dck.original_nx] == 0
                        and dual_porv_values[coarse_index + dck.original_nx] > 0
                        and not np.isnan(trany_values[original_index])
                    ):
                        positive_y += trany_values[original_index]
                    if (
                        row_index > 0
                        and mask_values[original_index - dck.original_nx] == 0
                        and mask_values[original_index] == 1
                        and dual_porv_values[coarse_index - dck.original_nx] > 0
                        and not np.isnan(trany_values[original_index - dck.original_nx])
                    ):
                        negative_y += trany_values[original_index - dck.original_nx]
                    original_layer += 1
                    matrix_row = row_index + 1
                    fracture_row = row_index + dck.original_ny + 2
                    output_layer = layer_index + 1
                    if vertical > 0:
                        nnc_lines.append(
                            f"{column_index + 1} {matrix_row} {output_layer} "
                            f"{column_index + 1} {fracture_row} {output_layer} "
                            f"{round_like_e([vertical],num_dig)[0]} /\n"
                        )
                    if positive_x > 0:
                        nnc_lines.append(
                            f"{column_index + 1} {matrix_row} {output_layer} "
                            f"{column_index + 2} {fracture_row} {output_layer} "
                            f"{round_like_e([positive_x],num_dig)[0]} /\n"
                        )
                    if negative_x > 0:
                        nnc_lines.append(
                            f"{column_index + 1} {matrix_row} {output_layer} "
                            f"{column_index} {fracture_row} {output_layer} "
                            f"{round_like_e([negative_x],num_dig)[0]} /\n"
                        )
                    if positive_y > 0:
                        nnc_lines.append(
                            f"{column_index + 1} {matrix_row} {output_layer} "
                            f"{column_index + 1} {fracture_row + 1} "
                            f"{output_layer} {round_like_e([positive_y],num_dig)[0]} /\n"
                        )
                    if negative_y > 0:
                        nnc_lines.append(
                            f"{column_index + 1} {matrix_row} {output_layer} "
                            f"{column_index + 1} {fracture_row - 1} "
                            f"{output_layer} {round_like_e([negative_y],num_dig)[0]} /\n"
                        )
    coarsening.nnc_text += "".join(nnc_lines)

    for property_name in ["actnum", "tranx", "trany"]:
        default_value = coarsening.dual_defaults.get(property_name, 0)
        if property_name == "tranx":
            source_values = coarsening.coarse_tranx
        elif property_name == "trany":
            source_values = coarsening.coarse_trany
        else:
            source_values = dck.output_actnum
        property_blocks: list[NDArray] = []
        for layer_index in range(dck.output_nz):
            layer_slice = slice(
                layer_index * cells_per_layer,
                (layer_index + 1) * cells_per_layer,
            )
            property_blocks.append(source_values[layer_slice])
            property_blocks.append(
                np.full(
                    dck.output_nx,
                    default_value,
                    dtype=source_values.dtype,
                )
            )
            if property_name == "tranx":
                property_blocks.append(np.asarray(coarsening.dual_tranx)[layer_slice])
            elif property_name == "trany":
                property_blocks.append(np.asarray(coarsening.dual_trany)[layer_slice])
            else:
                property_blocks.append(source_values[layer_slice])
        if property_name == "tranx":
            coarsening.coarse_tranx = np.concatenate(property_blocks)
        elif property_name == "trany":
            coarsening.coarse_trany = np.concatenate(property_blocks)
        else:
            setattr(dck, f"output_{property_name}", np.concatenate(property_blocks))
    return cr, zc


def _collect_removed_zcorn_indices(
    dck: ConfigViaDeck, coa_z: NDArray, removal_indices: list[int]
) -> list[int]:
    """Add the ZCORN indices removed by vertical coarsening."""
    cells_per_layer = 4 * dck.original_nx * dck.original_ny
    for layer_index in range(dck.original_nz + 1):
        if coa_z[layer_index] > 1:
            removal_indices.extend(
                range(
                    (2 * layer_index - 1) * cells_per_layer,
                    (2 * layer_index + 1) * cells_per_layer,
                )
            )
    return removal_indices


def map_nnc_transmissibilities(dck: ConfigViaDeck, coarsening: CoarseningMaps) -> None:
    """Map original non-neighbouring transmissibilities to the coarse grid.

    Connections that become Cartesian neighbours are accumulated in ``TRANX`` or
    ``TRANY``; remaining connections are written as NNC records.

    Parameters
    ----------
    dck
        Deck configuration and source NNC data.
    coarsening
        Coarse mapping updated with transmissibilities and NNC text."""
    output_directory = Path(dck.output_directory)
    original_grid = OpmFile(f"{dck.input_deck_name}.EGRID")
    coarsened_init = OpmFile(str(output_directory / f"{dck.output_deck_name}.INIT"))
    num_dig = dck.significant_digits
    first_connection_cells = np.asarray(original_grid["NNC1"], dtype=np.intp).reshape(
        -1
    )
    second_connection_cells = np.asarray(original_grid["NNC2"], dtype=np.intp).reshape(
        -1
    )
    connection_transmissibilities = np.asarray(
        dck.init_file["TRANNNC"],
        dtype=float,
    ).reshape(-1)
    connection_count = min(
        first_connection_cells.size,
        second_connection_cells.size,
        connection_transmissibilities.size,
    )
    first_cell_indices = first_connection_cells[:connection_count] - 1
    second_cell_indices = second_connection_cells[:connection_count] - 1
    connection_transmissibilities = connection_transmissibilities[:connection_count]
    original_cell_count = dck.original_nx * dck.original_ny * dck.original_nz
    coarsened_porv = np.asarray(coarsened_init["PORV"], dtype=float).reshape(-1)
    tranx_c = np.zeros(coarsened_porv.size, dtype=float)
    trany_c = np.zeros(coarsened_porv.size, dtype=float)
    active_cells = coarsened_porv > 0
    input_tranx = np.asarray(coarsened_init["TRANX"], dtype=float).reshape(-1)
    input_trany = np.asarray(coarsened_init["TRANY"], dtype=float).reshape(-1)
    if input_tranx.size == coarsened_porv.size:
        tranx_c[active_cells] = input_tranx[active_cells]
    elif input_tranx.size == np.count_nonzero(active_cells):
        tranx_c[active_cells] = input_tranx
    if input_trany.size == coarsened_porv.size:
        trany_c[active_cells] = input_trany[active_cells]
    elif input_trany.size == np.count_nonzero(active_cells):
        trany_c[active_cells] = input_trany
    cells_per_layer = dck.original_nx * dck.original_ny
    first_cell_i = first_cell_indices % dck.original_nx
    first_cell_j = first_cell_indices // dck.original_nx % dck.original_ny
    first_cell_k = first_cell_indices // cells_per_layer
    second_cell_i = second_cell_indices % dck.original_nx
    second_cell_j = second_cell_indices // dck.original_nx % dck.original_ny
    second_cell_k = second_cell_indices // cells_per_layer
    output_i_map = np.fromiter(
        (
            dck.original_to_output_i[original_index]
            for original_index in range(1, dck.original_nx + 1)
        ),
        dtype=np.intp,
        count=dck.original_nx,
    )
    output_j_map = np.fromiter(
        (
            dck.original_to_output_j[original_index]
            for original_index in range(1, dck.original_ny + 1)
        ),
        dtype=np.intp,
        count=dck.original_ny,
    )
    output_k_map = np.fromiter(
        (
            dck.original_to_output_k[original_index]
            for original_index in range(1, dck.original_nz + 1)
        ),
        dtype=np.intp,
        count=dck.original_nz,
    )
    first_output_i = output_i_map[first_cell_i]
    first_output_j = output_j_map[first_cell_j]
    first_output_k = output_k_map[first_cell_k]
    second_output_i = output_i_map[second_cell_i]
    second_output_j = output_j_map[second_cell_j]
    second_output_k = output_k_map[second_cell_k]
    coarsening_mask = np.asarray(coarsening.matrix_mask).reshape(-1)
    if coarsening_mask.size < original_cell_count:
        raise ValueError("The coarsening mask is smaller than the original grid")
    first_cell_mask = coarsening_mask[first_cell_indices]
    second_cell_mask = coarsening_mask[second_cell_indices]
    different_continuum = first_cell_mask != second_cell_mask
    same_output_layer = first_output_k == second_output_k
    different_horizontal_cell = (first_cell_i != second_cell_i) | (
        first_cell_j != second_cell_j
    )
    horizontal_candidate = (
        ~different_continuum & same_output_layer & different_horizontal_cell
    )
    positive_i_neighbour = horizontal_candidate & (first_cell_i + 1 == second_cell_i)
    negative_i_neighbour = horizontal_candidate & (first_cell_i == second_cell_i + 1)
    positive_j_neighbour = horizontal_candidate & (first_cell_j + 1 == second_cell_j)
    negative_j_neighbour = horizontal_candidate & (first_cell_j == second_cell_j + 1)
    first_coarse_indices = (
        first_output_i
        - 1
        + (first_output_j - 1) * dck.output_nx
        + (first_output_k - 1) * dck.output_nx * dck.output_ny
    )
    second_coarse_indices = (
        second_output_i
        - 1
        + (second_output_j - 1) * dck.output_nx
        + (second_output_k - 1) * dck.output_nx * dck.output_ny
    )
    positive_i_matrix = positive_i_neighbour & (first_cell_mask == 0)
    positive_i_fracture = positive_i_neighbour & (first_cell_mask != 0)
    negative_i_matrix = negative_i_neighbour & (first_cell_mask == 0)
    negative_i_fracture = negative_i_neighbour & (first_cell_mask != 0)
    positive_j_matrix = positive_j_neighbour & (first_cell_mask == 0)
    positive_j_fracture = positive_j_neighbour & (first_cell_mask != 0)
    negative_j_matrix = negative_j_neighbour & (first_cell_mask == 0)
    negative_j_fracture = negative_j_neighbour & (first_cell_mask != 0)
    np.add.at(
        coarsening.dual_tranx,
        first_coarse_indices[positive_i_matrix],
        connection_transmissibilities[positive_i_matrix],
    )
    np.add.at(
        tranx_c,
        first_coarse_indices[positive_i_fracture],
        connection_transmissibilities[positive_i_fracture],
    )
    np.add.at(
        coarsening.dual_tranx,
        second_coarse_indices[negative_i_matrix],
        connection_transmissibilities[negative_i_matrix],
    )
    np.add.at(
        tranx_c,
        second_coarse_indices[negative_i_fracture],
        connection_transmissibilities[negative_i_fracture],
    )
    np.add.at(
        coarsening.dual_trany,
        first_coarse_indices[positive_j_matrix],
        connection_transmissibilities[positive_j_matrix],
    )
    np.add.at(
        trany_c,
        first_coarse_indices[positive_j_fracture],
        connection_transmissibilities[positive_j_fracture],
    )
    np.add.at(
        coarsening.dual_trany,
        second_coarse_indices[negative_j_matrix],
        connection_transmissibilities[negative_j_matrix],
    )
    np.add.at(
        trany_c,
        second_coarse_indices[negative_j_fracture],
        connection_transmissibilities[negative_j_fracture],
    )
    nncc_mask = different_continuum | (~different_continuum & ~same_output_layer)
    nncc_indices = np.flatnonzero(nncc_mask)
    nncc_lines: list[str] = []
    for connection_index in nncc_indices:
        if different_continuum[connection_index]:
            if first_cell_mask[connection_index] == 1:
                first_i = first_output_i[connection_index]
                first_j = first_output_j[connection_index]
                first_k = first_output_k[connection_index]
                second_i = second_output_i[connection_index]
                second_j = second_output_j[connection_index] + 1 + dck.original_ny
                second_k = second_output_k[connection_index]
            else:
                first_i = second_output_i[connection_index]
                first_j = second_output_j[connection_index]
                first_k = second_output_k[connection_index]
                second_i = first_output_i[connection_index]
                second_j = first_output_j[connection_index] + 1 + dck.original_ny
                second_k = first_output_k[connection_index]
        elif first_cell_mask[connection_index] == 1:
            first_i = first_output_i[connection_index]
            first_j = first_output_j[connection_index]
            first_k = first_output_k[connection_index]
            second_i = second_output_i[connection_index]
            second_j = second_output_j[connection_index]
            second_k = second_output_k[connection_index]
        else:
            first_i = first_output_i[connection_index]
            first_j = first_output_j[connection_index] + 1 + dck.original_ny
            first_k = first_output_k[connection_index]
            second_i = second_output_i[connection_index]
            second_j = second_output_j[connection_index] + 1 + dck.original_ny
            second_k = second_output_k[connection_index]
        nncc_lines.append(
            f"{first_i} {first_j} {first_k} "
            f"{second_i} {second_j} {second_k} "
            f"{round_like_e([connection_transmissibilities[connection_index]],num_dig)[0]} /\n"
        )
    if nncc_lines:
        coarsening.nnc_text += "".join(nncc_lines)
    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_ctx = alive_bar(connection_count, bar="fish")
    else:
        bar_ctx = nullcontext()
    print("Handling the dual connectivity")
    print("Processing non-neighbouring transmissibilities (input model)")
    with bar_ctx as bar_animation:
        if show_progress and connection_count:
            bar_animation(connection_count)
    if not dck.dual_porosity_criterion:
        property_path = output_directory / f"{dck.include_prefix}TRANX.INC"
        write_property(property_path, "TRANX", tranx_c, num_dig)
        property_path = output_directory / f"{dck.include_prefix}TRANY.INC"
        write_property(property_path, "TRANY", trany_c, num_dig)
    else:
        coarsening.coarse_tranx = tranx_c
        coarsening.coarse_trany = trany_c


def create_coarsening_map(cfg: ConfigViaTOML) -> NDArray:
    """Map each fine-grid cell to a one-based coarse-cell identifier.

    The output dimensions and original-to-output axis mappings in ``cfg`` are also
    updated.

    Parameters
    ----------
    cfg
        TOML configuration containing the axis coarsening arrays.

    Returns
    -------
    NDArray
        One-based coarse-cell identifier for every fine-grid cell."""
    cell_number = 0
    coarse_cell_number = 1
    nx_fine, ny_fine, nz_fine = cfg.original_nx, cfg.original_ny, cfg.original_nz
    coa_map = np.zeros(cfg.original_cell_count, dtype=int)
    for layer_index in range(nz_fine):
        for row_index in range(ny_fine):
            for column_index in range(nx_fine):
                if coa_map[cell_number] == 0:
                    coa_map[cell_number] = coarse_cell_number
                    coarse_cell_number += 1
                if (
                    column_index + 1 < nx_fine
                    and cfg.x_coarsening[column_index + 1] > 1
                ):
                    coa_map[cell_number + 1] = coa_map[cell_number]
                if row_index + 1 < ny_fine and cfg.y_coarsening[row_index + 1] > 1:
                    coa_map[cell_number + nx_fine] = coa_map[cell_number]
                if layer_index + 1 < nz_fine and cfg.z_coarsening[layer_index + 1] > 1:
                    coa_map[cell_number + nx_fine * ny_fine] = coa_map[cell_number]
                cell_number += 1
    cfg.output_nx = nx_fine - int(np.count_nonzero(cfg.x_coarsening == 2))
    cfg.output_ny = ny_fine - int(np.count_nonzero(cfg.y_coarsening == 2))
    cfg.output_nz = nz_fine - int(np.count_nonzero(cfg.z_coarsening == 2))

    cfg.original_to_output_i = np.zeros(nx_fine + 1, dtype=int)
    coarse_index, fine_index = 1, 1
    for axis_index in range(nx_fine):
        if cfg.original_to_output_i[fine_index] == 0:
            cfg.original_to_output_i[fine_index] = coarse_index
            coarse_index += 1
        if axis_index + 1 < nx_fine and cfg.x_coarsening[axis_index + 1] > 1:
            cfg.original_to_output_i[fine_index + 1] = cfg.original_to_output_i[
                axis_index + 1
            ]
        fine_index += 1

    cfg.original_to_output_j = np.zeros(ny_fine + 1, dtype=int)
    coarse_index, fine_index = 1, 1
    for axis_index in range(ny_fine):
        if cfg.original_to_output_j[fine_index] == 0:
            cfg.original_to_output_j[fine_index] = coarse_index
            coarse_index += 1
        if axis_index + 1 < ny_fine and cfg.y_coarsening[axis_index + 1] > 1:
            cfg.original_to_output_j[fine_index + 1] = cfg.original_to_output_j[
                axis_index + 1
            ]
        fine_index += 1

    cfg.original_to_output_k = np.zeros(nz_fine + 1, dtype=int)
    coarse_index, fine_index = 1, 1
    for axis_index in range(nz_fine):
        if cfg.original_to_output_k[fine_index] == 0:
            cfg.original_to_output_k[fine_index] = coarse_index
            coarse_index += 1
        if axis_index + 1 < nz_fine and cfg.z_coarsening[axis_index + 1] > 1:
            cfg.original_to_output_k[fine_index + 1] = cfg.original_to_output_k[
                axis_index + 1
            ]
        fine_index += 1

    return coa_map


def _group_minimum_zero_based(
    values: NDArray,
    groups: NDArray,
    number_groups: int,
) -> NDArray:
    result = np.full(number_groups, np.inf)
    np.minimum.at(result, groups, values)
    return result


def _group_maximum_zero_based(
    values: NDArray,
    groups: NDArray,
    number_groups: int,
) -> NDArray:
    result = np.full(number_groups, -np.inf)
    np.maximum.at(result, groups, values)
    return result


def _group_sum_zero_based(
    values: NDArray,
    groups: NDArray,
    number_groups: int,
) -> NDArray:
    return np.bincount(groups, weights=values, minlength=number_groups)


def _read_satnum(
    cfg: ConfigViaTOML, actnum: NDArray, nxyz: int, satnum_opm: NDArray
) -> NDArray:
    """Read or generate fine-grid SATNUM values.

    Parameters
    ----------
    cfg
        TOML configuration controlling the SATNUM source.
    actnum
        Fine-grid active-cell mask.
    nxyz
        Number of fine-grid cells.
    satnum_opm
        SATNUM values read from the reference INIT file.

    Returns
    -------
    NDArray
        SATNUM value for every fine-grid cell."""
    reference_folder = (
        Path(cfg.resource_directory) / "reference_simulation" / cfg.model_name
    )
    satnum = np.ones(nxyz, dtype=int)
    if cfg.model_name == "norne":
        satnum = np.load(reference_folder / "satnum.npy")
    elif cfg.satnum_generation_method > 0:
        satnum_files = {1: "satnum_5.out", 3: "satnum_60.out"}
        if cfg.satnum_generation_method not in satnum_files:
            raise ValueError("satnum_generation_method must be 0, 1, or 3")
        satnum_values = []
        with open(
            reference_folder / satnum_files[cfg.satnum_generation_method],
            "r",
            encoding="utf8",
        ) as file:
            for row in csv.reader(file, delimiter="#"):
                satnum_values.append(int(row[0]))
        satnum = np.asarray(satnum_values)
    else:
        satnum[actnum] = satnum_opm
    return satnum


def coarsen_and_write_properties(cfg: ConfigViaTOML, coa_map: NDArray) -> int:
    """Aggregate and write properties for a TOML-generated model.

    Parameters
    ----------
    cfg
        TOML configuration and reference-case settings.
    coa_map
        One-based fine-to-coarse cell mapping.

    Returns
    -------
    int
        Highest generated SATNUM value, used as the number of saturation tables."""
    reference_folder = (
        Path(cfg.resource_directory) / "reference_simulation" / cfg.model_name
    )
    case_path = (
        Path(cfg.resource_directory)
        / "reference_simulation"
        / cfg.model_name
        / cfg.reference_case_name
    )
    print("Coarsening and writing the static properties")
    preprocessing_path = Path(cfg.output_directory) / "preprocessing"
    num_cells = cfg.output_nx * cfg.output_ny * cfg.output_nz
    num_dig = cfg.significant_digits
    groups = np.asarray(coa_map) - 1
    nxyz = cfg.original_cell_count
    opm = OpmGrid(f"{case_path}.EGRID")
    vol = np.asarray(opm.cellvolumes()) + 1e-10
    vol_c = _group_sum_zero_based(vol, groups, num_cells)
    opm = OpmFile(f"{case_path}.INIT")
    porv = np.asarray(opm["PORV"])
    actnum = porv > 0
    actnum_c = _group_minimum_zero_based(actnum, groups, num_cells).astype(int)
    active = actnum_c > 0
    active_volumes = vol * actnum
    props = ["poro", "ntg"]
    for property_name in props:
        values = np.zeros(nxyz, dtype=float)
        values[actnum] = opm[property_name.upper()]
        values_c = np.zeros(num_cells, dtype=float)
        values_c[active] = (
            _group_sum_zero_based(values * active_volumes, groups, num_cells)[active]
            / vol_c[active]
        )
        write_compact_property_file(
            preprocessing_path, property_name, values_c, num_dig
        )

    porv_c = np.zeros(num_cells, dtype=float)
    porv_c[active] = _group_sum_zero_based(porv, groups, num_cells)[active]
    if cfg.pore_volume_correction == 1:
        coarse_pore_volume = np.sum(porv_c)
        correction = np.sum(porv) / coarse_pore_volume
        porv_c *= correction
    write_compact_property_file(preprocessing_path, "porv", porv_c, num_dig)

    props = ["fipnum", "eqlnum"]
    if cfg.model_name == "norne":
        props += ["fluxnum"]
    else:
        props += ["multnum", "pvtnum", "fipzon"]

    for property_name in props:
        values = np.zeros(nxyz, dtype=int)
        values[actnum] = opm[property_name.upper()]
        values_c = _group_minimum_zero_based(values, groups, num_cells).astype(int)
        write_compact_property_file(
            preprocessing_path, property_name, values_c, num_dig
        )

    satnum_c = np.ones(num_cells, dtype=int)
    if cfg.model_name == "drogon" or (
        cfg.saturation_function_method == 1 and cfg.satnum_generation_method in (1, 3)
    ):
        values = _read_satnum(cfg, actnum, nxyz, opm["SATNUM"])
        satnum_c[:] = _group_minimum_zero_based(values, groups, num_cells).astype(int)

    if cfg.saturation_function_method == 1 and cfg.satnum_generation_method == 2:
        preceding_active_cells = np.concatenate(([0], np.cumsum(actnum_c[:-1])))
        mask = preceding_active_cells > 1
        satnum_c[mask] += preceding_active_cells[mask] - 1

    write_compact_property_file(preprocessing_path, "satnum", satnum_c, num_dig)

    endpoint_lines = []
    for property_name in ("swl", "sgu", "swcr"):
        values_c = np.zeros(num_cells, dtype=float)
        for coarse_index in np.flatnonzero(active):
            values = np.zeros(nxyz, dtype=float)
            values[actnum] = opm[property_name.upper()]
            fine_indices = np.flatnonzero(groups == coarse_index)
            fine_pore_volume = porv[fine_indices]
            coarse_pore_volume = np.sum(fine_pore_volume)
            values_c[coarse_index] = (
                np.sum(values[fine_indices] * fine_pore_volume) / coarse_pore_volume
            )
        endpoint_lines.append(f"{property_name.upper()}\n")
        endpoint_lines.extend(
            format_opm_compact_values(round_like_e(values_c, num_dig))
        )
        endpoint_lines.append("/\n")

    write_include(preprocessing_path / "endpoints.inc", "".join(endpoint_lines))

    if cfg.model_name == "norne":
        values = np.load(reference_folder / "multz.npy")
        multz_c = np.zeros(num_cells, dtype=float)
        multz_minimum = _group_minimum_zero_based(values, groups, num_cells)
        multz_c[active] = multz_minimum[active]
        write_property(
            preprocessing_path / "regionbarriers.inc", "MULTZ", multz_c, num_dig
        )

    active = actnum_c > 0
    active_volumes = vol * actnum

    project_path = Path(cfg.output_directory)
    template_path = Path(cfg.resource_directory) / "template_scripts"
    active_indices = np.flatnonzero(np.asarray(actnum_c) == 1)
    last_active_index = int(active_indices[-1]) if active_indices.size else 0

    for axis_index, property_name in enumerate(["permx", "permy", "permz"]):
        values = np.zeros(nxyz, dtype=float)
        values[actnum] = opm[property_name.upper()]
        values_c = np.zeros(num_cells, dtype=float)

        if cfg.rock_property_settings[axis_index][2] == "max":
            maximum = _group_maximum_zero_based(values, groups, num_cells)
            values_c[active] = maximum[active]
        else:
            weighted_sum = _group_sum_zero_based(
                values * active_volumes, groups, num_cells
            )
            values_c[active] = weighted_sum[active] / vol_c[active]

        write_compact_property_file(
            preprocessing_path, property_name, values_c, num_dig
        )

        values_c_min_max = np.zeros((num_cells, 2), dtype=float)
        minimum = np.full(num_cells, np.inf)
        maximum = np.full(num_cells, -np.inf)
        np.minimum.at(minimum, groups, values)
        np.maximum.at(maximum, groups, values)
        values_c_min_max[:, 0] = minimum
        values_c_min_max[:, 1] = 1.1 * maximum

        if cfg.rock_property_settings[axis_index][1] == 1 and cfg.execution_mode in (
            "files",
            "ert",
        ):
            property_name = cfg.rock_property_settings[axis_index][0]
            variables = {
                "rock_property_settings": cfg.rock_property_settings,
                "execution_mode": cfg.execution_mode,
                "last_active_index": last_active_index,
                "values_c": values_c,
                "values_c_min_max": values_c_min_max,
                "i": axis_index,
                "active": active,
            }
            _render_template(
                template_path / "common" / "perm.mako",
                project_path / "parameters" / f"{property_name}.tmpl",
                **variables,
            )
            _render_template(
                template_path / "common" / "perm_priors.mako",
                project_path / "parameters" / f"{property_name}_priors.data",
                **variables,
            )
            _render_template(
                template_path / "common" / "perm_eval.mako",
                project_path / "jobs" / f"{property_name}_eval.py",
                **variables,
            )

    props = ["swat"]
    if cfg.initialization_method != 0:
        props += ["sgas", "pressure", "rs", "rv"]

    swat = np.zeros(nxyz, dtype=float)
    opm = OpmRestart(f"{case_path}.UNRST")

    init_lines = []
    for property_name in props:
        values = np.zeros(nxyz, dtype=float)
        values[actnum] = opm[property_name.upper(), 0]
        if property_name == "swat":
            swat = values.copy()

        values_c = np.zeros(num_cells, dtype=float)
        weighted_sum = _group_sum_zero_based(values * porv, groups, num_cells)
        values_c[active] = weighted_sum[active] / porv_c[active]
        init_lines.append(f"{property_name.upper()}\n")
        init_lines.extend(format_opm_compact_values(round_like_e(values_c, num_dig)))
        init_lines.append("/\n")
    write_include(preprocessing_path / "init.inc", "".join(init_lines))

    swatinit_c = np.zeros(num_cells, dtype=float)
    swatinit_sum = _group_sum_zero_based(swat * porv, groups, num_cells)
    swatinit_c[active] = swatinit_sum[active] / porv_c[active]

    write_property(preprocessing_path / "swatinit.inc", "SWATINIT", swatinit_c, num_dig)

    return int(np.max(satnum_c))
