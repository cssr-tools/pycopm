# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,E1102

"""Transform corner-point grid coordinates and rewrite associated properties."""

import sys
from contextlib import nullcontext

import numpy as np
from alive_progress import alive_bar

from pycopm.config.config import ConfigViaDeck
from pycopm.utils.files_writer import write_grid, write_property_inc


def transform_grid(dck: ConfigViaDeck) -> None:
    """Apply the configured transformation to the corner-point grid.

    Supported specifications are ``translate [x,y,z]``, ``scale [x,y,z]``, and
    ``rotatexy``, ``rotatexz``, or ``rotateyz`` followed by an angle in degrees.
    Rotations are performed about the coordinate-system origin.

    Parameters
    ----------
    dck
        Deck configuration containing ``grid_transformation`` and source geometry."""
    transformation = dck.grid_transformation.split()
    transformation_name = transformation[0]

    original_zcorn = np.asarray(dck.egrid_file["ZCORN"], dtype=float)
    original_coord = np.asarray(dck.egrid_file["COORD"], dtype=float)
    transformed_coord = original_coord.reshape(-1, 2, 3).copy()

    if transformation_name in ("translate", "scale"):
        transformation_values = np.fromstring(
            transformation[1].strip("()[]"), sep=",", dtype=float
        )

        if transformation_name == "translate":
            transformed_coord += transformation_values
            zc = original_zcorn + transformation_values[2]
        else:
            transformed_coord *= transformation_values
            zc = original_zcorn * transformation_values[2]

    else:
        angle = np.deg2rad(float(transformation[1]))
        cosine = np.cos(angle)
        sine = np.sin(angle)

        if transformation_name == "rotatexy":
            xy_values = transformed_coord[:, :, :2].copy()
            transformed_coord[:, :, 0] = (
                xy_values[:, :, 0] * cosine - xy_values[:, :, 1] * sine
            )
            transformed_coord[:, :, 1] = (
                xy_values[:, :, 1] * cosine + xy_values[:, :, 0] * sine
            )
            zc = original_zcorn.copy()

        else:
            coordinate_axis = 0 if transformation_name == "rotatexz" else 1
            corner_pairs = np.asarray(((0, 1), (2, 3), (4, 5), (6, 7)))
            horizontal_coordinates = np.empty(original_zcorn.size, dtype=float)
            horizontal_index = 0

            for layer_index in range(dck.original_nz):
                layer_coordinates = np.asarray(
                    [
                        [
                            dck.grid_model.xyz_from_ijk(
                                column_index, row_index, layer_index
                            )[coordinate_axis]
                            for column_index in range(dck.original_nx)
                        ]
                        for row_index in range(dck.original_ny)
                    ],
                    dtype=float,
                )
                coordinate_values = (
                    layer_coordinates[:, :, corner_pairs]
                    .transpose(2, 0, 1, 3)
                    .reshape(-1)
                )
                next_index = horizontal_index + coordinate_values.size
                horizontal_coordinates[horizontal_index:next_index] = coordinate_values
                horizontal_index = next_index

            horizontal_coordinates = horizontal_coordinates.reshape(
                original_zcorn.shape
            )

            if transformation_name == "rotatexz":
                xz_values = transformed_coord[:, :, (0, 2)].copy()
                transformed_coord[:, :, 0] = (
                    xz_values[:, :, 0] * cosine + xz_values[:, :, 1] * sine
                )
                transformed_coord[:, :, 2] = (
                    xz_values[:, :, 1] * cosine - xz_values[:, :, 0] * sine
                )
                zc = original_zcorn * cosine - horizontal_coordinates * sine
            else:
                yz_values = transformed_coord[:, :, (1, 2)].copy()
                transformed_coord[:, :, 1] = (
                    yz_values[:, :, 0] * cosine - yz_values[:, :, 1] * sine
                )
                transformed_coord[:, :, 2] = (
                    yz_values[:, :, 1] * cosine + yz_values[:, :, 0] * sine
                )
                zc = original_zcorn * cosine + horizontal_coordinates * sine

    cr = transformed_coord.ravel()
    write_grid(dck, cr, zc, False)


def transform_properties(dck: ConfigViaDeck, modified_deck: list[str]) -> None:
    """Rewrite reservoir properties for a transformed grid.

    Property values are unchanged because transformations modify only geometry.

    Parameters
    ----------
    dck
        Deck configuration containing source properties and output dimensions.
    modified_deck
        Deck lines updated with generated property includes."""
    property_names = (
        dck.props_keywords
        + dck.regions_keywords
        + dck.grids_keywords
        + dck.solution_keywords
        + ["porv"]
    )
    number_values = dck.output_nx * dck.output_ny * dck.output_nz
    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_progress = alive_bar(len(property_names), bar="fish")
    else:
        bar_progress = nullcontext()
    with bar_progress as bar_animation:
        for property_name in property_names:
            if show_progress:
                bar_animation()
            values = np.zeros(dck.original_cell_count)
            if property_name in dck.solution_keywords:
                values[dck.original_active_cell_mask] = dck.restart_file[
                    property_name.upper(), 0
                ]
            elif property_name == "porv":
                values = np.asarray(dck.init_file[property_name.upper()])
            else:
                values[dck.original_active_cell_mask] = dck.init_file[
                    property_name.upper()
                ]
            write_property_inc(
                dck,
                property_name,
                values,
                number_values,
                modified_deck,
                True,
            )
