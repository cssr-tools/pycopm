# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0902,R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,E1102

"""Extract submodels and map pore volume from outside their boundaries."""

import csv
import sys
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from alive_progress import alive_bar
from numpy.typing import NDArray
from shapely import Polygon, contains_xy, prepare

from pycopm.config.config import ConfigViaDeck
from pycopm.utils.files_writer import write_grid, write_property_inc


@dataclass(slots=True)
class VicinityMaps:
    """Store a vicinity selection, bounds, and pore-volume mappings.

    Global and per-layer bounds are one-based and inclusive.
    """

    #: Selected well name, or an empty string for polygon and region
    #: selections.
    selector: str

    #: Well-vicinity shape: ``box``, ``diamond``, or ``diamondxy``. ``None`` is
    #: used for polygon and region selections.
    shape: str | None

    #: Boolean mask identifying selected original-grid cells, flattened in
    #: ``(z, y, x)`` order.
    cell_mask: NDArray

    #: Minimum selected i index across all layers.
    min_i: int

    #: Maximum selected i index across all layers.
    max_i: int

    #: Minimum selected j index across all layers.
    min_j: int

    #: Maximum selected j index across all layers.
    max_j: int

    #: Minimum selected k index.
    min_k: int

    #: Maximum selected k index.
    max_k: int

    #: Minimum selected i index in each original layer.
    layer_min_i: NDArray

    #: Maximum selected i index in each original layer.
    layer_max_i: NDArray

    #: Minimum selected j index in each original layer.
    layer_min_j: NDArray

    #: Maximum selected j index in each original layer.
    layer_max_j: NDArray

    #: Total pore volume of selected active cells in each original layer.
    layer_selected_porv: NDArray

    #: Total pore volume outside the selection in each original layer.
    layer_external_porv: NDArray

    #: Zero-based completion coordinates in ``[i, j, k]`` order for the
    #: selected well.
    well_cells: list[list[int]]

    #: Zero-based output-grid indices of selected well cells. These cells are
    #: excluded from boundary source remapping.
    well_indices: list[int] = field(default_factory=list)

    #: Number of selected active cells in each output layer.
    active_counts: NDArray = field(default_factory=lambda: np.array([], dtype=int))

    #: Original-grid source index assigned to each output boundary cell during
    #: pore-volume correction. Zero denotes no assigned source.
    source_indices: NDArray = field(default_factory=lambda: np.array([], dtype=int))


@dataclass(slots=True)
class _BoundaryMapping:
    """Store pore-volume mapping results for one submodel boundary."""

    #: Unassigned pore volume collected along the boundary.
    pore_volume: float

    #: Number of active cells receiving pore volume from the boundary.
    active_count: int

    #: Distance from the geometric boundary to each receiving cell.
    offsets: NDArray


def _submodel_index(dck: ConfigViaDeck, column: int, row: int, layer: int) -> int:
    return column + row * dck.output_nx + layer * dck.output_nx * dck.output_ny


def _original_index(dck: ConfigViaDeck, column: int, row: int, layer: int) -> int:
    return column + row * dck.original_nx + layer * dck.original_nx * dck.original_ny


def _add_or_collect_porv(
    dck: ConfigViaDeck, submodel_index: int, pore_volume: float
) -> float:
    if dck.pore_volume_correction in (1, 2):
        dck.output_porv[submodel_index] += pore_volume
        return 0.0
    return pore_volume


def create_vicinity_maps(dck: ConfigViaDeck) -> VicinityMaps:
    """Select submodel cells and calculate their bounds.

    Selections can use region values, an xy polygon, or a well-centred ``box``,
    ``diamond``, or ``diamondxy`` neighbourhood.

    Parameters
    ----------
    dck
        Deck configuration containing the vicinity specification and source grid.

    Returns
    -------
    VicinityMaps
        Selection mask, bounds, well cells, and per-layer pore-volume totals."""
    vicinity_options = dck.vicinity_specification.split()
    selector = vicinity_options[0]
    is_selector_well = False
    shape: str | None = None
    total_cells = dck.original_nx * dck.original_ny * dck.original_nz
    cells_per_layer = dck.original_nx * dck.original_ny
    well_cells = []
    if selector.upper() == "XYPOLYGON":
        cell_centers = np.empty((total_cells, 3), dtype=float)
        for global_index in range(total_cells):
            layer_index, layer_offset = divmod(global_index, cells_per_layer)
            row_index, column_index = divmod(layer_offset, dck.original_nx)
            cell_coordinates = np.asarray(
                dck.grid_model.xyz_from_ijk(column_index, row_index, layer_index, True),
                dtype=float,
            )
            cell_centers[global_index] = np.mean(cell_coordinates, axis=1)
        polygon_coordinates = np.asarray(
            [
                (
                    float(coordinate.split(",")[0][1:]),
                    float(coordinate.split(",")[1][:-1]),
                )
                for coordinate in vicinity_options[1:]
            ],
            dtype=float,
        )
        grid_minimum = np.minimum(
            np.min(cell_centers[:, :2], axis=0),
            np.min(polygon_coordinates, axis=0),
        )
        grid_maximum = np.maximum(
            np.max(cell_centers[:, :2], axis=0),
            np.max(polygon_coordinates, axis=0),
        )
        coordinate_range = grid_maximum - grid_minimum
        normalized_centers = (cell_centers[:, :2] - grid_minimum) / coordinate_range
        normalized_polygon = (polygon_coordinates - grid_minimum) / coordinate_range
        polygon = Polygon(normalized_polygon)
        prepare(polygon)
        cell_mask = contains_xy(
            polygon, normalized_centers[:, 0], normalized_centers[:, 1]
        )
    elif len(vicinity_options) > 2:
        is_selector_well = True
        shape = vicinity_options[1].lower()
        well_cells = _get_well_completions_for_vicinity(dck, selector)
        cell_mask = np.zeros(total_cells, dtype=bool)
        well_locations = np.asarray(well_cells, dtype=np.intp).reshape(-1, 3)
        if shape == "diamond":
            interval = int(vicinity_options[2])
            offset_range = np.arange(-interval, interval + 1, dtype=np.intp)
            layer_offsets, row_offsets, column_offsets = np.meshgrid(
                offset_range, offset_range, offset_range, indexing="ij"
            )
            offset_mask = (
                (np.abs(row_offsets - column_offsets - layer_offsets) <= interval)
                & (np.abs(column_offsets + row_offsets - layer_offsets) <= interval)
                & (np.abs(row_offsets - column_offsets + layer_offsets) <= interval)
                & (np.abs(column_offsets + row_offsets + layer_offsets) <= interval)
            )
            vicinity_offsets = np.column_stack(
                (
                    column_offsets[offset_mask],
                    row_offsets[offset_mask],
                    layer_offsets[offset_mask],
                )
            )
            for well_location in well_locations:
                selected_locations = well_location + vicinity_offsets
                location_mask = (
                    (selected_locations[:, 0] >= 0)
                    & (selected_locations[:, 0] < dck.original_nx)
                    & (selected_locations[:, 1] >= 0)
                    & (selected_locations[:, 1] < dck.original_ny)
                    & (selected_locations[:, 2] >= 0)
                    & (selected_locations[:, 2] < dck.original_nz)
                )
                selected_locations = selected_locations[location_mask]
                global_indices = (
                    selected_locations[:, 0]
                    + selected_locations[:, 1] * dck.original_nx
                    + selected_locations[:, 2] * cells_per_layer
                )
                cell_mask[global_indices] = True
        elif shape == "diamondxy":
            interval = int(vicinity_options[2])
            offset_range = np.arange(-interval, interval + 1, dtype=np.intp)
            row_offsets_xy, column_offsets_xy = np.meshgrid(
                offset_range, offset_range, indexing="ij"
            )
            offset_mask = (np.abs(row_offsets_xy - column_offsets_xy) <= interval) & (
                np.abs(column_offsets_xy + row_offsets_xy) <= interval
            )
            horizontal_offsets = np.column_stack(
                (column_offsets_xy[offset_mask], row_offsets_xy[offset_mask])
            )
            all_layer_offsets = (
                np.arange(dck.original_nz, dtype=np.intp)[:, None] * cells_per_layer
            )
            for well_location in well_locations:
                selected_columns = well_location[0] + horizontal_offsets[:, 0]
                selected_rows = well_location[1] + horizontal_offsets[:, 1]
                location_mask = (
                    (selected_columns >= 0)
                    & (selected_columns < dck.original_nx)
                    & (selected_rows >= 0)
                    & (selected_rows < dck.original_ny)
                )
                horizontal_indices = (
                    selected_columns[location_mask]
                    + selected_rows[location_mask] * dck.original_nx
                )
                global_indices = (
                    all_layer_offsets + horizontal_indices[None, :]
                ).ravel()
                cell_mask[global_indices] = True
        else:
            intervals = np.asarray(
                [
                    (
                        int(interval.split(",")[0][1:]),
                        int(interval.split(",")[1][:-1]),
                    )
                    for interval in vicinity_options[2:]
                ],
                dtype=int,
            )
            if intervals.shape != (3, 2):
                raise ValueError(
                    "The vicinity intervals must define x, y, and z ranges."
                )
            column_offsets = np.arange(
                intervals[0, 0], intervals[0, 1] + 1, dtype=np.intp
            )
            row_offsets = np.arange(intervals[1, 0], intervals[1, 1] + 1, dtype=np.intp)
            layer_offsets = np.arange(
                intervals[2, 0], intervals[2, 1] + 1, dtype=np.intp
            )
            layer_offsets, row_offsets, column_offsets = np.meshgrid(
                layer_offsets, row_offsets, column_offsets, indexing="ij"
            )
            vicinity_offsets = np.column_stack(
                (
                    column_offsets.ravel(),
                    row_offsets.ravel(),
                    layer_offsets.ravel(),
                )
            )
            for well_location in well_locations:
                selected_locations = well_location + vicinity_offsets
                location_mask = (
                    (selected_locations[:, 0] >= 0)
                    & (selected_locations[:, 0] < dck.original_nx)
                    & (selected_locations[:, 1] >= 0)
                    & (selected_locations[:, 1] < dck.original_ny)
                    & (selected_locations[:, 2] >= 0)
                    & (selected_locations[:, 2] < dck.original_nz)
                )
                selected_locations = selected_locations[location_mask]
                global_indices = (
                    selected_locations[:, 0]
                    + selected_locations[:, 1] * dck.original_nx
                    + selected_locations[:, 2] * cells_per_layer
                )
                cell_mask[global_indices] = True
    else:
        selected_values = np.asarray(
            [int(value) for value in vicinity_options[1].split(",")]
        )
        keyword = selector.upper()
        cell_mask = np.zeros(total_cells, dtype=bool)
        active_property_values = np.asarray(dck.init_file[keyword])
        cell_mask[dck.original_active_cell_mask] = np.isin(
            active_property_values, selected_values
        )
    selected_active_cells = np.asarray(cell_mask, dtype=bool) & (
        np.asarray(dck.original_porv) > 0
    )
    selected_indices = np.flatnonzero(selected_active_cells)
    layer_indices, layer_offsets = np.divmod(selected_indices, cells_per_layer)
    row_indices, column_indices = np.divmod(layer_offsets, dck.original_nx)
    min_i = int(np.min(column_indices)) + 1
    max_i = int(np.max(column_indices)) + 1
    min_j = int(np.min(row_indices)) + 1
    max_j = int(np.max(row_indices)) + 1
    min_k = int(np.min(layer_indices)) + 1
    max_k = int(np.max(layer_indices)) + 1
    layer_min_i = np.full(dck.original_nz, dck.original_nx, dtype=int)
    layer_max_i = np.ones(dck.original_nz, dtype=int)
    layer_min_j = np.full(dck.original_nz, dck.original_ny, dtype=int)
    layer_max_j = np.ones(dck.original_nz, dtype=int)
    np.minimum.at(layer_min_i, layer_indices, column_indices + 1)
    np.maximum.at(layer_max_i, layer_indices, column_indices + 1)
    np.minimum.at(layer_min_j, layer_indices, row_indices + 1)
    np.maximum.at(layer_max_j, layer_indices, row_indices + 1)
    pore_volumes = np.asarray(dck.original_porv, dtype=float)
    layer_selected_porv = np.bincount(
        layer_indices,
        weights=pore_volumes[selected_indices],
        minlength=dck.original_nz,
    )
    all_layer_indices = np.repeat(np.arange(dck.original_nz), cells_per_layer)
    layer_external_porv = np.bincount(
        all_layer_indices,
        weights=pore_volumes * ~selected_active_cells,
        minlength=dck.original_nz,
    )
    return VicinityMaps(
        selector=selector if is_selector_well else "",
        shape=shape,
        cell_mask=np.asarray(cell_mask, dtype=bool),
        min_i=min_i,
        max_i=max_i,
        min_j=min_j,
        max_j=max_j,
        min_k=min_k,
        max_k=max_k,
        layer_min_i=layer_min_i,
        layer_max_i=layer_max_i,
        layer_min_j=layer_min_j,
        layer_max_j=layer_max_j,
        layer_selected_porv=layer_selected_porv,
        layer_external_porv=layer_external_porv,
        well_cells=well_cells,
    )


def map_vicinity_properties(
    dck: ConfigViaDeck, vicinity: VicinityMaps, modified_deck: list[str]
) -> None:
    """Map reservoir properties into the submodel bounding box.

    Cells inside the bounding box but outside the selection are written as
    inactive. The function updates output pore volume and active cells.

    Parameters
    ----------
    dck
        Deck configuration containing source properties and output dimensions.
    vicinity
        Selection and bounds created by :func:`create_vicinity_maps`.
    modified_deck
        Deck lines updated with generated property includes."""
    submodel_cells = dck.output_nx * dck.output_ny * dck.output_nz
    dck.original_active_cell_mask = np.asarray(dck.original_porv) > 0
    vicinity.active_counts = np.zeros(dck.output_nz)
    vicinity.source_indices = np.zeros(submodel_cells, dtype=int)
    property_names = (
        ["porv"]
        + dck.solution_keywords
        + dck.props_keywords
        + dck.regions_keywords
        + dck.grids_keywords
    )
    column_indices = np.arange(vicinity.min_i - 1, vicinity.max_i, dtype=np.intp)
    row_indices = np.arange(vicinity.min_j - 1, vicinity.max_j, dtype=np.intp)
    layer_indices = np.arange(vicinity.min_k - 1, vicinity.max_k, dtype=np.intp)
    selected_global_indices = (
        column_indices[None, None, :]
        + row_indices[None, :, None] * dck.original_nx
        + layer_indices[:, None, None] * dck.original_nx * dck.original_ny
    ).ravel()
    selected_layer_indices = np.broadcast_to(
        np.arange(dck.output_nz, dtype=np.intp)[:, None, None],
        (dck.output_nz, dck.output_ny, dck.output_nx),
    ).ravel()
    selected_cell_mask = (
        dck.original_active_cell_mask[selected_global_indices]
        & np.asarray(vicinity.cell_mask, dtype=bool)[selected_global_indices]
    )
    selected_output_indices = np.flatnonzero(selected_cell_mask)
    effective_global_indices = selected_global_indices[selected_cell_mask]
    active_global_indices = np.flatnonzero(dck.original_active_cell_mask)
    active_source_indices = np.searchsorted(
        active_global_indices, effective_global_indices
    )
    vicinity.active_counts[:] = np.bincount(
        selected_layer_indices[selected_cell_mask],
        minlength=dck.output_nz,
    )
    solution_keywords = set(dck.solution_keywords)
    show_progress = sys.stdout.isatty()
    if show_progress:
        bar_ctx = alive_bar(len(property_names), bar="fish")
    else:
        bar_ctx = nullcontext()
    with bar_ctx as bar_animation:
        for property_name in property_names:
            if show_progress:
                bar_animation()
            property_dtype = int if "num" in property_name else float
            values_c = np.zeros(submodel_cells, dtype=property_dtype)
            if property_name == "porv":
                source_values = np.asarray(dck.original_porv)
                values_c[selected_output_indices] = source_values[
                    effective_global_indices
                ]
                dck.output_porv = values_c
            elif property_name in solution_keywords:
                source_values = np.asarray(dck.restart_file[property_name.upper(), 0])
                values_c[selected_output_indices] = source_values[active_source_indices]
            else:
                source_values = np.asarray(dck.init_file[property_name.upper()])
                values_c[selected_output_indices] = source_values[active_source_indices]
            write_property_inc(
                dck,
                property_name,
                values_c,
                submodel_cells,
                modified_deck,
                True,
            )
    dck.output_actnum = (np.asarray(dck.output_porv) > 0).astype(int)


def extract_vicinity_grid(dck: ConfigViaDeck, vicinity: VicinityMaps) -> None:
    """Extract and write the selected corner-point subgrid.

    Parameters
    ----------
    dck
        Deck configuration containing source geometry and axis mappings.
    vicinity
        Inclusive bounds of the selected submodel."""
    original_zcorn = np.asarray(dck.egrid_file["ZCORN"])
    original_coord = np.asarray(dck.egrid_file["COORD"])
    source_coord = original_coord.reshape(dck.original_ny + 1, dck.original_nx + 1, 6)
    cr = source_coord[
        vicinity.min_j - 1 : vicinity.max_j + 1,
        vicinity.min_i - 1 : vicinity.max_i + 1,
        :,
    ].ravel()
    selected_columns = np.asarray(dck.original_to_output_i[1 : dck.original_nx + 1]) > 0
    selected_rows = np.asarray(dck.original_to_output_j[1 : dck.original_ny + 1]) > 0
    selected_layers = np.asarray(dck.original_to_output_k[1 : dck.original_nz + 1]) > 0
    doubled_column_indices = np.flatnonzero(np.repeat(selected_columns, 2))
    doubled_row_indices = np.flatnonzero(np.repeat(selected_rows, 2))
    surface_indices = np.flatnonzero(np.repeat(selected_layers, 2))
    source_zcorn = original_zcorn.reshape(
        2 * dck.original_nz,
        2 * dck.original_ny,
        2 * dck.original_nx,
    )
    zc = source_zcorn[
        np.ix_(
            surface_indices,
            doubled_row_indices,
            doubled_column_indices,
        )
    ].ravel()
    write_grid(dck, cr, zc, False)


def _map_south_boundary(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    layer_index: int,
    original_layer: int,
    column_offset: int,
    row_offset: int,
    trailing_columns: int,
) -> _BoundaryMapping:
    offsets = np.zeros(dck.output_nx, dtype=int)
    collected_porv = 0.0
    active_count = 0
    width = dck.output_nx - column_offset - trailing_columns
    south_rows = int(vicinity.layer_min_j[original_layer]) - 1
    original_column_start = int(vicinity.layer_min_i[original_layer]) - 1
    pore_volume_grid = np.asarray(dck.original_porv).reshape(
        dck.original_nz, dck.original_ny, dck.original_nx
    )
    for local_column in range(width):
        submodel_column = local_column + column_offset
        submodel_cell = _submodel_index(dck, submodel_column, row_offset, layer_index)
        original_column = local_column + original_column_start
        boundary_cell = _original_index(
            dck, original_column, max(south_rows - 1, 0), original_layer
        )
        boundary_porv = float(
            np.sum(pore_volume_grid[original_layer, :south_rows, original_column])
        )
        if dck.output_actnum[submodel_cell] > 0:
            if submodel_cell not in vicinity.well_indices:
                vicinity.source_indices[submodel_cell] = boundary_cell + dck.original_nx
            active_count += 1
            collected_porv += _add_or_collect_porv(dck, submodel_cell, boundary_porv)
            continue
        interior_cell = boundary_cell + 1
        if (
            interior_cell >= dck.original_porv.size
            or dck.original_porv[interior_cell] <= 0
        ):
            collected_porv += boundary_porv
            continue
        for inward_offset in range(dck.output_ny - 1 - row_offset):
            submodel_cell = _submodel_index(
                dck,
                submodel_column,
                inward_offset + 1 + row_offset,
                layer_index,
            )
            original_row = inward_offset + south_rows
            original_cell = _original_index(
                dck, original_column, original_row, original_layer
            )
            boundary_porv += 0.5 * dck.original_porv[original_cell]
            if dck.output_actnum[submodel_cell] > 0:
                if submodel_cell not in vicinity.well_indices:
                    vicinity.source_indices[submodel_cell] = original_cell
                offsets[local_column] = inward_offset + 1
                active_count += 1
                collected_porv += _add_or_collect_porv(
                    dck, submodel_cell, boundary_porv
                )
                break
            if inward_offset == dck.output_ny - 2 - row_offset:
                collected_porv += boundary_porv
    return _BoundaryMapping(collected_porv, active_count, offsets)


def _map_north_boundary(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    layer_index: int,
    original_layer: int,
    column_offset: int,
    trailing_rows: int,
    trailing_columns: int,
) -> _BoundaryMapping:
    offsets = np.zeros(dck.output_nx, dtype=int)
    collected_porv = 0.0
    active_count = 0
    width = dck.output_nx - column_offset - trailing_columns
    north_start = int(vicinity.layer_max_j[original_layer])
    original_column_start = int(vicinity.layer_min_i[original_layer]) - 1
    pore_volume_grid = np.asarray(dck.original_porv).reshape(
        dck.original_nz, dck.original_ny, dck.original_nx
    )
    for local_column in range(width):
        submodel_column = local_column + column_offset
        submodel_cell = _submodel_index(
            dck, submodel_column, dck.output_ny - 1 - trailing_rows, layer_index
        )
        original_column = local_column + original_column_start
        boundary_porv = float(
            np.sum(pore_volume_grid[original_layer, north_start:, original_column])
        )
        interior_cell = _original_index(
            dck, original_column, north_start - 1, original_layer
        )
        if dck.output_actnum[submodel_cell] > 0:
            if trailing_rows == 0 and submodel_cell not in vicinity.well_indices:
                vicinity.source_indices[submodel_cell] = interior_cell
            active_count += 1
            collected_porv += _add_or_collect_porv(dck, submodel_cell, boundary_porv)
            continue
        if dck.original_porv[interior_cell] <= 0:
            collected_porv += boundary_porv
            continue
        for inward_offset in range(dck.output_ny - 1 - trailing_rows):
            submodel_row = dck.output_ny - 2 - inward_offset - trailing_rows
            submodel_cell = _submodel_index(
                dck, submodel_column, submodel_row, layer_index
            )
            original_row = north_start - inward_offset - 1
            original_cell = _original_index(
                dck, original_column, original_row, original_layer
            )
            boundary_porv += 0.5 * dck.original_porv[original_cell]
            if dck.output_actnum[submodel_cell] > 0:
                if submodel_cell not in vicinity.well_indices:
                    vicinity.source_indices[submodel_cell] = (
                        original_cell - dck.original_nx
                    )
                offsets[local_column] = inward_offset + 1
                active_count += 1
                collected_porv += _add_or_collect_porv(
                    dck, submodel_cell, boundary_porv
                )
                break
            if inward_offset == dck.output_ny - 2 - trailing_rows:
                collected_porv += boundary_porv
    return _BoundaryMapping(collected_porv, active_count, offsets)


def _map_east_boundary(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    layer_index: int,
    original_layer: int,
    column_offset: int,
    row_offset: int,
    trailing_rows: int,
) -> _BoundaryMapping:
    offsets = np.zeros(dck.output_ny, dtype=int)
    collected_porv = 0.0
    active_count = 0
    height = dck.output_ny - row_offset - trailing_rows
    east_columns = int(vicinity.layer_min_i[original_layer]) - 1
    original_row_start = int(vicinity.layer_min_j[original_layer]) - 1
    pore_volume_grid = np.asarray(dck.original_porv).reshape(
        dck.original_nz, dck.original_ny, dck.original_nx
    )
    for local_row in range(height):
        submodel_row = local_row + row_offset
        submodel_cell = _submodel_index(dck, column_offset, submodel_row, layer_index)
        original_row = local_row + original_row_start
        boundary_porv = float(
            np.sum(pore_volume_grid[original_layer, original_row, :east_columns])
        )
        interior_cell = _original_index(
            dck, max(east_columns - 1, 0), original_row, original_layer
        )
        if dck.output_actnum[submodel_cell] > 0:
            if submodel_cell not in vicinity.well_indices:
                vicinity.source_indices[submodel_cell] = interior_cell + 1
            active_count += 1
            collected_porv += _add_or_collect_porv(dck, submodel_cell, boundary_porv)
            continue
        adjacent_cell = interior_cell + 1
        if (
            adjacent_cell >= dck.original_porv.size
            or dck.original_porv[adjacent_cell] <= 0
        ):
            collected_porv += boundary_porv
            continue
        for inward_offset in range(dck.output_nx - 1 - column_offset):
            submodel_cell = _submodel_index(
                dck,
                inward_offset + column_offset + 1,
                submodel_row,
                layer_index,
            )
            original_column = inward_offset + east_columns
            original_cell = _original_index(
                dck, original_column, original_row, original_layer
            )
            boundary_porv += 0.5 * dck.original_porv[original_cell]
            if dck.output_actnum[submodel_cell] > 0:
                if submodel_cell not in vicinity.well_indices:
                    vicinity.source_indices[submodel_cell] = original_cell + 1
                offsets[local_row] = inward_offset + 1
                active_count += 1
                collected_porv += _add_or_collect_porv(
                    dck, submodel_cell, boundary_porv
                )
                break
            if inward_offset == dck.output_nx - 2 - column_offset:
                collected_porv += boundary_porv
    return _BoundaryMapping(collected_porv, active_count, offsets)


def _get_well_completions_for_vicinity(dck: ConfigViaDeck, optvic) -> list:
    """Collect zero-based completions for a selected well.

    Parameters
    ----------
    dck
        Deck configuration identifying the source DATA file.
    optvic
        Well name from the vicinity specification.

    Returns
    -------
    list[list[int]]
        Completion coordinates in ``[i, j, k]`` order."""
    in_compdat = False
    deck_path = Path(f"{dck.input_deck_name}.DATA")
    wvicinity = []
    with deck_path.open("r", encoding=dck.deck_encoding) as deck_file:
        for row in csv.reader(deck_file):
            parsed_line = str(row)[2:-2].strip()
            if parsed_line == "COMPDAT":
                in_compdat = True
                continue
            if not in_compdat:
                continue
            tokens = parsed_line.split()
            if not tokens:
                continue
            if tokens[0] == "/":
                in_compdat = False
                continue
            if tokens[0].startswith("--"):
                continue
            well_name = tokens[0].replace("'", "")
            if well_name != optvic or len(tokens) <= 4:
                continue
            source_i = int(tokens[1])
            source_j = int(tokens[2])
            source_k1 = int(tokens[3])
            source_k2 = int(tokens[4])
            for source_k in range(source_k1, source_k2 + 1):
                wvicinity.append([source_i - 1, source_j - 1, source_k - 1])
    return wvicinity


def _map_west_boundary(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    layer_index: int,
    original_layer: int,
    row_offset: int,
    trailing_rows: int,
    trailing_columns: int,
) -> _BoundaryMapping:
    offsets = np.zeros(dck.output_ny, dtype=int)
    collected_porv = 0.0
    active_count = 0
    height = dck.output_ny - row_offset - trailing_rows
    west_start = int(vicinity.layer_max_i[original_layer])
    original_row_start = int(vicinity.layer_min_j[original_layer]) - 1
    pore_volume_grid = np.asarray(dck.original_porv).reshape(
        dck.original_nz, dck.original_ny, dck.original_nx
    )
    for local_row in range(height):
        submodel_row = local_row + row_offset
        submodel_cell = _submodel_index(
            dck,
            dck.output_nx - 1 - trailing_columns,
            submodel_row,
            layer_index,
        )
        original_row = local_row + original_row_start
        boundary_porv = float(
            np.sum(pore_volume_grid[original_layer, original_row, west_start:])
        )
        interior_cell = _original_index(
            dck, west_start - 1, original_row, original_layer
        )
        if dck.output_actnum[submodel_cell] > 0:
            if trailing_columns == 0 and submodel_cell not in vicinity.well_indices:
                vicinity.source_indices[submodel_cell] = interior_cell
            active_count += 1
            collected_porv += _add_or_collect_porv(dck, submodel_cell, boundary_porv)
            continue
        if dck.original_porv[interior_cell] <= 0:
            collected_porv += boundary_porv
            continue
        for inward_offset in range(dck.output_nx - 1 - trailing_columns):
            submodel_column = dck.output_nx - 2 - inward_offset - trailing_columns
            submodel_cell = _submodel_index(
                dck, submodel_column, submodel_row, layer_index
            )
            original_column = west_start - inward_offset - 1
            original_cell = _original_index(
                dck, original_column, original_row, original_layer
            )
            boundary_porv += 0.5 * dck.original_porv[original_cell]
            if dck.output_actnum[submodel_cell] > 0:
                if submodel_cell not in vicinity.well_indices:
                    vicinity.source_indices[submodel_cell] = original_cell - 1
                offsets[local_row] = inward_offset + 1
                active_count += 1
                collected_porv += _add_or_collect_porv(
                    dck, submodel_cell, boundary_porv
                )
                break
            if inward_offset == dck.output_nx - 2 - trailing_columns:
                collected_porv += boundary_porv
    return _BoundaryMapping(collected_porv, active_count, offsets)


def _corner_pore_volumes(
    dck: ConfigViaDeck, vicinity: VicinityMaps, original_layer: int
) -> tuple[float, float, float, float]:
    """Calculate excluded pore volume in the four layer corners.

    Returns
    -------
    southwest, southeast, northwest, northeast
        Corner pore-volume totals for the selected original layer."""
    pore_volume_grid = np.asarray(dck.original_porv).reshape(
        dck.original_nz, dck.original_ny, dck.original_nx
    )
    minimum_column = int(vicinity.layer_min_i[original_layer]) - 1
    maximum_column = int(vicinity.layer_max_i[original_layer])
    minimum_row = int(vicinity.layer_min_j[original_layer]) - 1
    maximum_row = int(vicinity.layer_max_j[original_layer])
    layer_porv = pore_volume_grid[original_layer]
    return (
        float(np.sum(layer_porv[:minimum_row, :minimum_column])),
        float(np.sum(layer_porv[:minimum_row, maximum_column:])),
        float(np.sum(layer_porv[maximum_row:, :minimum_column])),
        float(np.sum(layer_porv[maximum_row:, maximum_column:])),
    )


def _apply_layer_pore_volume_correction(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    layer_index: int,
    column_offset: int,
    row_offset: int,
    trailing_columns: int,
    trailing_rows: int,
    south: _BoundaryMapping,
    north: _BoundaryMapping,
    east: _BoundaryMapping,
    west: _BoundaryMapping,
    corner_porv: tuple[float, float, float, float],
) -> None:
    layer_start = layer_index * dck.output_nx * dck.output_ny
    layer_end = layer_start + dck.output_nx * dck.output_ny
    boundary_indices = (
        np.flatnonzero(vicinity.source_indices[layer_start:layer_end] != 0)
        + layer_start
    )
    boundary_count = int(boundary_indices.size)
    if dck.pore_volume_correction == 3:
        if vicinity.shape != "diamond" and boundary_count > 0:
            dck.output_porv[boundary_indices] += (
                vicinity.layer_external_porv[layer_index] / boundary_count
            )
        return
    if dck.pore_volume_correction == 4:
        if vicinity.shape != "diamond" and vicinity.active_counts[layer_index] > 0:
            active_indices = (
                np.flatnonzero(dck.output_actnum[layer_start:layer_end] > 0)
                + layer_start
            )
            dck.output_porv[active_indices] += (
                vicinity.layer_external_porv[layer_index]
                / vicinity.active_counts[layer_index]
            )
        return
    southwest_porv, southeast_porv, northwest_porv, northeast_porv = corner_porv
    width = dck.output_nx - column_offset - trailing_columns
    for local_column in range(width):
        south_cell = _submodel_index(
            dck,
            local_column + column_offset,
            south.offsets[local_column] + row_offset,
            layer_index,
        )
        if dck.output_actnum[south_cell] > 0 and south.active_count > 0:
            increment = south.pore_volume / south.active_count
            if dck.pore_volume_correction == 1:
                if south.active_count + east.active_count > 0:
                    increment += southwest_porv / (
                        south.active_count + east.active_count
                    )
                if south.active_count + west.active_count > 0:
                    increment += southeast_porv / (
                        south.active_count + west.active_count
                    )
            dck.output_porv[south_cell] += increment
        north_cell = _submodel_index(
            dck,
            local_column + column_offset,
            dck.output_ny - 1 - north.offsets[local_column] - trailing_rows,
            layer_index,
        )
        if dck.output_actnum[north_cell] > 0 and north.active_count > 0:
            increment = north.pore_volume / north.active_count
            if dck.pore_volume_correction == 1:
                if north.active_count + east.active_count > 0:
                    increment += northwest_porv / (
                        north.active_count + east.active_count
                    )
                if north.active_count + west.active_count > 0:
                    increment += northeast_porv / (
                        north.active_count + west.active_count
                    )
            dck.output_porv[north_cell] += increment
    height = dck.output_ny - row_offset - trailing_rows
    for local_row in range(height):
        east_cell = _submodel_index(
            dck,
            east.offsets[local_row] + column_offset,
            local_row + row_offset,
            layer_index,
        )
        if dck.output_actnum[east_cell] > 0 and east.active_count > 0:
            increment = east.pore_volume / east.active_count
            if dck.pore_volume_correction == 1:
                if east.active_count + south.active_count > 0:
                    increment += southwest_porv / (
                        east.active_count + south.active_count
                    )
                if east.active_count + north.active_count > 0:
                    increment += northwest_porv / (
                        east.active_count + north.active_count
                    )
            dck.output_porv[east_cell] += increment
        west_cell = _submodel_index(
            dck,
            dck.output_nx - 1 - west.offsets[local_row] - trailing_columns,
            local_row + row_offset,
            layer_index,
        )
        if dck.output_actnum[west_cell] > 0 and west.active_count > 0:
            increment = west.pore_volume / west.active_count
            if dck.pore_volume_correction == 1:
                if west.active_count + south.active_count > 0:
                    increment += southeast_porv / (
                        west.active_count + south.active_count
                    )
                if west.active_count + north.active_count > 0:
                    increment += northeast_porv / (
                        west.active_count + north.active_count
                    )
            dck.output_porv[west_cell] += increment
    if dck.pore_volume_correction == 2:
        for corner_column, corner_row, corner_value in (
            (0, 0, southwest_porv),
            (dck.output_nx - 1, 0, southeast_porv),
            (0, dck.output_ny - 1, northwest_porv),
            (dck.output_nx - 1, dck.output_ny - 1, northeast_porv),
        ):
            if corner_value != 0:
                nearest_index = _find_nearest_active_corner_cell(
                    dck, layer_index, corner_column, corner_row
                )
                dck.output_porv[nearest_index] += corner_value
    expected_porv = (
        vicinity.layer_external_porv[layer_index]
        + vicinity.layer_selected_porv[layer_index]
    )
    mapped_porv = float(np.sum(dck.output_porv[layer_start:layer_end]))
    if mapped_porv < expected_porv and boundary_count > 0:
        dck.output_porv[boundary_indices] += (
            expected_porv - mapped_porv
        ) / boundary_count


def _find_nearest_active_corner_cell(
    dck: ConfigViaDeck, layer_index: int, corner_i: int, corner_j: int
) -> int:
    """Return the nearest active cell to a corner in a layer."""
    layer_start = layer_index * dck.output_nx * dck.output_ny
    active_cells = np.asarray(dck.output_actnum)[
        layer_start : layer_start + dck.output_nx * dck.output_ny
    ].reshape(dck.output_ny, dck.output_nx)
    active_j, active_i = np.nonzero(active_cells > 0)
    if active_i.size == 0:
        raise ValueError(f"No active cells found in submodel layer {layer_index}")
    distances = np.abs(active_i - corner_i) + np.abs(active_j - corner_j)
    nearest = np.lexsort((active_i, active_j, distances))[0]
    return int(layer_start + active_i[nearest] + active_j[nearest] * dck.output_nx)


def _distribute_vertical_pore_volume(
    dck: ConfigViaDeck, vicinity: VicinityMaps
) -> None:
    """Distribute pore volume excluded above and below the submodel.

    Parameters
    ----------
    dck
        Deck configuration whose ``output_porv`` is updated.
    vicinity
        Selection bounds and correction settings."""
    if vicinity.shape == "diamond" or dck.pore_volume_correction in (3, 4):
        return
    cells_per_original_layer = dck.original_nx * dck.original_ny
    submodel_porv = dck.output_porv.reshape(dck.output_nz, dck.output_ny, dck.output_nx)
    active_columns = np.any(submodel_porv > 0, axis=0)
    column_rows, column_columns = np.nonzero(active_columns)
    if column_rows.size == 0:
        return
    if vicinity.min_k > 1:
        lower_end = (vicinity.min_k - 1) * cells_per_original_layer
        lower_porv = float(np.sum(dck.original_porv[:lower_end]))
        first_layers = np.argmax(submodel_porv > 0, axis=0)
        lower_indices = (
            first_layers[column_rows, column_columns] * dck.output_nx * dck.output_ny
            + column_rows * dck.output_nx
            + column_columns
        )
        dck.output_porv[lower_indices] += lower_porv / lower_indices.size
    if vicinity.max_k < dck.original_nz:
        upper_start = vicinity.max_k * cells_per_original_layer
        upper_porv = float(np.sum(dck.original_porv[upper_start:]))
        last_layers = dck.output_nz - 1 - np.argmax(submodel_porv[::-1] > 0, axis=0)
        upper_indices = (
            last_layers[column_rows, column_columns] * dck.output_nx * dck.output_ny
            + column_rows * dck.output_nx
            + column_columns
        )
        dck.output_porv[upper_indices] += upper_porv / upper_indices.size


def apply_boundary_pore_volume_correction(
    dck: ConfigViaDeck, vicinity: VicinityMaps
) -> None:
    """Map pore volume excluded from the submodel onto active cells.

    The correction strategy is selected by ``dck.pore_volume_correction``. Depending
    on the chosen method, excluded pore volume is assigned to corresponding
    boundary cells, nearest corner cells, all boundary cells, or all active cells.

    Parameters
    ----------
    dck
        Deck configuration whose ``output_porv`` is updated.
    vicinity
        Selection bounds and pore-volume mapping arrays."""
    if (
        vicinity.shape in ("diamond", "diamondxy")
        and int(dck.vicinity_specification.split()[2]) > 0
    ):
        for well_location in vicinity.well_cells:
            vicinity.well_indices.append(
                well_location[0]
                - vicinity.min_i
                + (well_location[1] - vicinity.min_j + 1) * dck.output_nx
                + (well_location[2] - vicinity.min_k + 1)
                * dck.output_nx
                * dck.output_ny
                + 1
            )
    original_porv = dck.output_porv.copy() if dck.pore_volume_correction == 0 else None
    for layer_index in range(dck.output_nz):
        original_layer = layer_index + vicinity.min_k - 1
        row_offset = int(vicinity.layer_min_j[original_layer]) - vicinity.min_j
        column_offset = int(vicinity.layer_min_i[original_layer]) - vicinity.min_i
        trailing_rows = vicinity.max_j - int(vicinity.layer_max_j[original_layer])
        trailing_columns = vicinity.max_i - int(vicinity.layer_max_i[original_layer])
        corner_porv = _corner_pore_volumes(dck, vicinity, original_layer)
        south = _map_south_boundary(
            dck,
            vicinity,
            layer_index,
            original_layer,
            column_offset,
            row_offset,
            trailing_columns,
        )
        north = _map_north_boundary(
            dck,
            vicinity,
            layer_index,
            original_layer,
            column_offset,
            trailing_rows,
            trailing_columns,
        )
        east = _map_east_boundary(
            dck,
            vicinity,
            layer_index,
            original_layer,
            column_offset,
            row_offset,
            trailing_rows,
        )
        west = _map_west_boundary(
            dck,
            vicinity,
            layer_index,
            original_layer,
            row_offset,
            trailing_rows,
            trailing_columns,
        )
        _apply_layer_pore_volume_correction(
            dck,
            vicinity,
            layer_index,
            column_offset,
            row_offset,
            trailing_columns,
            trailing_rows,
            south,
            north,
            east,
            west,
            corner_porv,
        )
    _distribute_vertical_pore_volume(dck, vicinity)
    mapped_porv = float(np.sum(dck.output_porv))
    expected_porv = float(
        np.sum(vicinity.layer_external_porv) + np.sum(vicinity.layer_selected_porv)
    )
    if dck.pore_volume_correction == 0 and original_porv is not None:
        dck.output_porv = original_porv
    elif dck.pore_volume_correction in (1, 2, 3):
        correction_indices = np.flatnonzero(vicinity.source_indices != 0)
        if correction_indices.size > 0:
            dck.output_porv[correction_indices] += (
                expected_porv - mapped_porv
            ) / correction_indices.size
    else:
        correction_frequency = int(np.sum(vicinity.active_counts))
        active_indices = np.flatnonzero(dck.output_actnum > 0)
        if correction_frequency > 0:
            dck.output_porv[active_indices] += (
                expected_porv - mapped_porv
            ) / correction_frequency
