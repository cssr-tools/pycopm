# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0902,R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,R1705

"""Parse an OPM deck and update records for the modified grid."""

import csv
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from pycopm.config.config import ConfigViaDeck
from pycopm.utils.vicinity import VicinityMaps

csv.field_size_limit(sys.maxsize)


@dataclass(slots=True)
class _ParserState:
    """Store temporary state while parsing an OPM deck.

    The Boolean fields indicate active keyword blocks. The list fields track wells,
    completions, and segmented-well records retained in the generated deck."""

    dimens: bool = False
    grid: bool = False
    welspecs: bool = False
    welsegs: bool = False
    complump: bool = False
    compdat: bool = False
    compsegs: bool = False
    mapaxes: bool = False
    multregt: bool = False
    process_edit: bool = False
    editnnc: bool = False
    multiply: bool = False
    props: bool = False
    operation: bool = False
    regions: bool = False
    equil: bool = False
    faults: bool = False
    multflt: bool = False
    welldims: bool = False
    skip_block: bool = False
    aqucon: bool = False
    aqunum: bool = False
    aquancon: bool = False
    bccon: bool = False
    bwpr: bool = False
    source: bool = False
    pinch: bool = False
    has_edit: bool = False

    previous_completion: list[str] = field(default_factory=list)
    compsegs_wells: list[str] = field(default_factory=list)
    retained_wells: list[str] = field(default_factory=list)
    completion_wells: list[str] = field(default_factory=list)
    segmented_wells: list[str] = field(default_factory=list)

    separator: str = ""
    schedule_keyword: str = ""


_SCHEDULE_KEYWORDS = frozenset(
    {
        "wconhist",
        "wdfac",
        "weltarg",
        "wrftplt",
        "compord",
        "wtracer",
        "wconinjh",
        "wconinje",
        "wconprod",
        "wtest",
        "welopen",
        "wsegvalv",
        "wecon",
        "cskin",
        "wpavedep",
    }
)


def process_deck(
    dck: ConfigViaDeck, vicinity: VicinityMaps
) -> tuple[list[str], list[int]]:
    """Rewrite deck records for the modified grid.

    The parser updates dimensions, properties, grid-index ranges, wells, aquifers,
    faults, and selected schedule records.

    Parameters
    ----------
    dck
        Deck configuration and axis index mappings.
    vicinity
        Vicinity selection used when extracting a submodel.

    Returns
    -------
    modified_deck, well_cell_indices
        Rewritten deck lines and coarse cells containing well completions."""
    modified_deck: list[str] = []
    wellcind: list[int] = []
    kwr = _ParserState()
    hvicinity = bool(vicinity and vicinity.shape)
    if dck.refinement_enabled:
        _collect_segmented_well_names(dck, kwr)
    elif dck.vicinity_specification:
        _collect_vicinity_well_names(dck, kwr, vicinity)
    deck_path = Path(f"{dck.input_deck_name}.DATA")
    with deck_path.open("r", encoding=dck.deck_encoding) as deck_file:
        for row in csv.reader(deck_file):
            parsed_line = str(row)[2:-2].strip()
            parsed_line = parsed_line.replace("\\t", " ")
            parsed_line = parsed_line.replace("', '", ",")
            parsed_line = parsed_line.replace("-- Generated : Petrel", "")
            parsed_line = parsed_line.strip()
            if not kwr.separator and parsed_line.count("-") > 70:
                kwr.separator = parsed_line
            if _handle_dimens(dck, kwr, modified_deck, parsed_line):
                continue
            if _handle_welldims(dck, kwr, modified_deck, parsed_line):
                continue
            if _handle_grid_props(dck, kwr, modified_deck, parsed_line):
                continue
            if _handle_props(dck, vicinity, kwr, modified_deck, parsed_line):
                continue
            if _handle_regions(dck, kwr, modified_deck, parsed_line):
                continue
            if _handle_equil(dck, kwr, modified_deck, parsed_line):
                continue
            if not dck.grid_transformation:
                if _handle_bwpr(dck, kwr, modified_deck, parsed_line):
                    continue
                if _handle_wells(dck, kwr, modified_deck, parsed_line, hvicinity):
                    continue
                if _handle_source(dck, kwr, modified_deck, parsed_line):
                    continue
                if _handle_aquancon(dck, kwr, modified_deck, parsed_line):
                    continue
                if dck.vicinity_specification:
                    if _handle_welsegs(kwr, modified_deck, parsed_line):
                        continue
                    if __handle_schedule_keyword(kwr, modified_deck, parsed_line):
                        continue
                if _handle_segmented_wells(
                    dck, kwr, modified_deck, parsed_line, wellcind
                ):
                    continue
            if modified_deck:
                for special_name in dck.special_keywords:
                    if (
                        f"{special_name}." in parsed_line.lower()
                        or f".{special_name}" in parsed_line.lower()
                    ) or (
                        modified_deck[-1] == "INCLUDE"
                        and special_name in parsed_line.lower()
                    ):
                        parsed_line = (
                            f"{dck.include_prefix}{special_name.upper()}.INC /"
                        )
            modified_deck.append(parsed_line)
            if (
                len(modified_deck) > 1
                and modified_deck[-2] == "INCLUDE"
                and _include_contains_endbox(dck, parsed_line)
            ):
                modified_deck[-2] = "--" + modified_deck[-2]
                modified_deck[-1] = "--" + modified_deck[-1]
    return modified_deck, wellcind


def _include_contains_endbox(dck: ConfigViaDeck, nrwo: str) -> bool:
    """Return whether an included file contains ENDBOX."""
    include_text = nrwo
    if "--" in include_text:
        include_text = include_text.split("--", maxsplit=1)[0]
    include_text = include_text.replace(" /", "")
    include_text = include_text.rstrip("/").strip().strip("'\"")
    deck_path = Path(f"{dck.input_deck_name}.DATA").absolute()
    include_path = (deck_path.parent / include_text).absolute()
    if not include_path.exists():
        print(f"Include not found: {include_path}")
        return False
    with include_path.open("r", encoding=dck.deck_encoding) as include_file:
        for row in csv.reader(include_file):
            parsed_line = str(row)[2:-2].strip()
            if parsed_line == "ENDBOX":
                return True
    return False


def __handle_schedule_keyword(
    kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Filter supported schedule records by wells retained in the submodel."""
    keyword_name = nrwo.lower()
    if keyword_name in _SCHEDULE_KEYWORDS:
        kwr.schedule_keyword = keyword_name
        modified_deck.append(nrwo)
        return True
    if not kwr.schedule_keyword:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        kwr.schedule_keyword = ""
    if len(tokens) <= 1:
        return False
    if tokens[0].startswith("--"):
        return True
    well_name = tokens[0].replace("'", "")
    if kwr.schedule_keyword == "wsegvalv" and well_name in kwr.segmented_wells:
        return True
    if well_name.endswith("*"):
        well_prefix = well_name[:-1]
        for retained_well in kwr.retained_wells:
            if retained_well.startswith(well_prefix):
                return False
    return well_name not in kwr.retained_wells


def _collect_vicinity_well_names(
    dck: ConfigViaDeck, kwr: _ParserState, vicinity: VicinityMaps
) -> None:
    """Identify wells and segmented wells retained in the vicinity model."""
    segmented_well = ""
    deck_path = Path(f"{dck.input_deck_name}.DATA")
    with deck_path.open("r", encoding=dck.deck_encoding) as deck_file:
        for row in csv.reader(deck_file):
            parsed_line = str(row)[2:-2].strip()
            if parsed_line == "COMPDAT":
                kwr.compdat = True
                continue
            if kwr.compdat:
                tokens = parsed_line.split()
                if tokens:
                    if tokens[0] == "/":
                        kwr.previous_completion = []
                        kwr.compdat = False
                    well_name = tokens[0].replace("'", "")
                    if well_name in kwr.retained_wells:
                        continue
                    if len(tokens) > 4 and not tokens[0].startswith("--"):
                        if well_name not in kwr.completion_wells:
                            kwr.completion_wells.append(well_name)
                        source_i = int(tokens[1])
                        source_j = int(tokens[2])
                        source_k1 = int(tokens[3])
                        source_k2 = int(tokens[4])
                        if (
                            dck.original_to_output_i[source_i]
                            * dck.original_to_output_j[source_j]
                            * dck.original_to_output_k[source_k1]
                            * dck.original_to_output_k[source_k2]
                            > 0
                        ):
                            kwr.retained_wells.append(well_name)
            if parsed_line == "COMPSEGS":
                kwr.compsegs = True
                continue
            if kwr.compsegs:
                tokens = parsed_line.split()
                if tokens and tokens[0] == "/":
                    kwr.compsegs = False
                if len(tokens) > 1 and not tokens[0].startswith("--"):
                    well_name = tokens[0].replace("'", "")
                    if well_name in kwr.completion_wells:
                        segmented_well = well_name
                    elif len(tokens) > 2:
                        source_i = int(tokens[0])
                        source_j = int(tokens[1])
                        source_k = int(tokens[2])
                        if (
                            dck.original_to_output_i[source_i]
                            * dck.original_to_output_j[source_j]
                            * dck.original_to_output_k[source_k]
                            != 0
                            and segmented_well not in kwr.segmented_wells
                        ):
                            kwr.segmented_wells.append(segmented_well)
    if vicinity and vicinity.selector:
        selected_well_names = {vicinity.selector, f"'{vicinity.selector}'"}
        kwr.segmented_wells = [
            well_name.replace("'", "")
            for well_name in kwr.segmented_wells
            if well_name in selected_well_names
        ]
        kwr.retained_wells = [
            well_name.replace("'", "")
            for well_name in kwr.retained_wells
            if well_name in selected_well_names
        ]
        kwr.completion_wells = [
            well_name.replace("'", "")
            for well_name in kwr.completion_wells
            if well_name in selected_well_names
        ]


def _collect_segmented_well_names(dck: ConfigViaDeck, kwr: _ParserState) -> None:
    """Identify wells requiring segmented-well completion handling."""
    deck_path = Path(f"{dck.input_deck_name}.DATA")
    with deck_path.open("r", encoding=dck.deck_encoding) as deck_file:
        for row in csv.reader(deck_file):
            parsed_line = str(row)[2:-2].strip()
            if parsed_line == "COMPDAT":
                kwr.compdat = True
                continue
            if kwr.compdat:
                tokens = parsed_line.split()
                if tokens:
                    if tokens[0] == "/":
                        kwr.compdat = False
                    well_name = tokens[0].replace("'", "")
                    if well_name in kwr.segmented_wells:
                        continue
                    if len(tokens) > 2 and not tokens[0].startswith("--"):
                        if not kwr.previous_completion:
                            kwr.previous_completion = tokens
                        else:
                            previous_well = kwr.previous_completion[0].replace("'", "")
                            changed_column = (
                                tokens[1] != kwr.previous_completion[1]
                                or tokens[2] != kwr.previous_completion[2]
                            )
                            if changed_column and well_name == previous_well:
                                kwr.segmented_wells.append(well_name)
                        kwr.previous_completion = tokens
            if parsed_line == "COMPSEGS":
                kwr.compsegs = True
                continue
            if kwr.compsegs:
                tokens = parsed_line.split()
                if len(tokens) > 1 and not tokens[0].startswith("--"):
                    well_name = tokens[0].replace("'", "")
                    kwr.compsegs_wells.append(well_name)
                    kwr.compsegs = False


def _handle_dimens(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Replace the original DIMENS values with the modified grid dimensions."""
    if nrwo == "DIMENS":
        kwr.dimens = True
        modified_deck.append(nrwo)
        modified_deck.append(f"{dck.output_nx} {dck.output_ny} {dck.output_nz} /")
        return True

    if not kwr.dimens:
        return False

    tokens = nrwo.split()
    if (
        tokens
        and not tokens[0].startswith("--")
        and (tokens[-1] == "/" or tokens[0] == "/")
    ):
        kwr.dimens = False
    return True


def _handle_welldims(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update WELLDIMS for a refined grid."""
    if not dck.refinement_enabled:
        return False
    if nrwo == "WELLDIMS":
        kwr.welldims = True
        modified_deck.append(nrwo)
        return True
    if not kwr.welldims:
        return False
    tokens = nrwo.split()
    if tokens and not tokens[0].startswith("--"):
        if len(tokens) > 2:
            tokens[1] = str(dck.output_nx + dck.output_ny + dck.output_nz)
            modified_deck.append(" ".join(tokens))
            if "/" in nrwo:
                kwr.welldims = False
        if tokens[0] == "/":
            modified_deck.append(nrwo)
            kwr.welldims = False
    return True


def _handle_props(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    kwr: _ParserState,
    modified_deck: list[str],
    nrwo: str,
) -> bool:
    """Handle the PROPS section and its supported operations."""
    if nrwo == "PROPS" and not kwr.props:
        kwr.props = True
        if kwr.separator:
            modified_deck.append(kwr.separator)
        modified_deck.append(nrwo)
        return True
    if not kwr.props:
        return False
    if _handle_oper(dck, vicinity, kwr, modified_deck, nrwo):
        return True
    if nrwo in {"REGIONS", "SOLUTION"}:
        kwr.props = False
    return False


def _handle_oper(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    kwr: _ParserState,
    modified_deck: list[str],
    nrwo: str,
) -> bool:
    """Update supported operation records for the modified grid."""
    if nrwo in {"EQUALS", "COPY", "ADD", "MULTIPLY"}:
        if nrwo == "COPY" and not kwr.props:
            return False
        kwr.operation = True
        modified_deck.append(nrwo)
        return True
    if not kwr.operation:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        kwr.operation = False
    if len(tokens) > 7 and not tokens[0].startswith("--"):
        if "PERM" in tokens[0]:
            tokens[1] = "1"
        source_i1 = int(tokens[2])
        source_i2 = int(tokens[3])
        source_j1 = int(tokens[4])
        source_j2 = int(tokens[5])
        source_k1 = int(tokens[6])
        source_k2 = int(tokens[7])
        if dck.refinement_enabled:
            tokens[2] = str(dck.original_to_first_refined_i[source_i1])
            tokens[3] = str(dck.original_to_last_refined_i[source_i2])
            tokens[4] = str(dck.original_to_first_refined_j[source_j1])
            tokens[5] = str(dck.original_to_last_refined_j[source_j2])
            tokens[6] = str(dck.original_to_first_refined_k[source_k1])
            tokens[7] = str(dck.original_to_last_refined_k[source_k2])
        elif dck.vicinity_specification:
            intersects_i = (
                vicinity.min_i - source_i1 + 1 > 0
                or source_i2 - vicinity.max_i + 1 > 0
                or dck.original_to_output_i[source_i2] > 0
            )
            intersects_j = (
                vicinity.min_j - source_j1 + 1 > 0
                or source_j2 - vicinity.max_j + 1 > 0
                or dck.original_to_output_j[source_j2] > 0
            )
            intersects_k = (
                vicinity.min_k - source_k1 + 1 > 0
                or source_k2 - vicinity.max_k + 1 > 0
                or dck.original_to_output_k[source_k2] > 0
            )
            if not (intersects_i and intersects_j and intersects_k):
                return True
            tokens[2] = str(max(1, dck.original_to_output_i[source_i1]))
            tokens[3] = str(
                dck.output_nx
                if dck.original_to_output_i[source_i2] == 0
                else dck.original_to_output_i[source_i2]
            )
            tokens[4] = str(max(1, dck.original_to_output_j[source_j1]))
            tokens[5] = str(
                dck.output_ny
                if dck.original_to_output_j[source_j2] == 0
                else dck.original_to_output_j[source_j2]
            )
            tokens[6] = str(max(1, dck.original_to_output_k[source_k1]))
            tokens[7] = str(
                dck.output_nz
                if dck.original_to_output_k[source_k2] == 0
                else dck.original_to_output_k[source_k2]
            )
        else:
            tokens[2] = str(dck.original_to_output_i[source_i1])
            tokens[3] = str(dck.original_to_output_i[source_i2])
            tokens[4] = str(dck.original_to_output_j[source_j1])
            tokens[5] = str(dck.original_to_output_j[source_j2])
            tokens[6] = str(dck.original_to_output_k[source_k1])
            tokens[7] = str(dck.original_to_output_k[source_k2])
        modified_deck.append(" ".join(tokens))
        return True
    if not kwr.props:
        modified_deck.append(nrwo)
    return False


def _handle_bwpr(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update BWPR grid indices for the modified grid."""
    if nrwo == "BWPR":
        kwr.bwpr = True
        modified_deck.append(nrwo)
        return True
    if not kwr.bwpr:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        kwr.bwpr = False
    if len(tokens) > 2 and not tokens[0].startswith("--"):
        source_i = int(tokens[0])
        source_j = int(tokens[1])
        source_k = int(tokens[2])
        if dck.vicinity_specification and (
            dck.original_to_output_i[source_i]
            * dck.original_to_output_j[source_j]
            * dck.original_to_output_k[source_k]
            == 0
        ):
            return True
        tokens[0] = str(dck.original_to_output_i[source_i])
        tokens[1] = str(dck.original_to_output_j[source_j])
        tokens[2] = str(dck.original_to_output_k[source_k])
        modified_deck.append(" ".join(tokens))
        return True
    return False


def _handle_regions(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Replace the REGIONS content with generated include files."""
    if nrwo == "REGIONS" and not kwr.regions:
        kwr.regions = True
        modified_deck.append(nrwo)
        if len(modified_deck) > 1 and modified_deck[-2].startswith("---"):
            modified_deck.append(modified_deck[-2])
        return True
    if not kwr.regions:
        return False
    if nrwo != "SOLUTION":
        return True
    kwr.regions = False
    for region_name in dck.regions_keywords:
        modified_deck.append("INCLUDE")
        modified_deck.append(f"'{dck.include_prefix}{region_name.upper()}.INC' /\n")
    if kwr.separator:
        modified_deck.append(kwr.separator)
    return False


def _handle_equil(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Replace EQUIL with explicit initialization include files."""
    if not dck.write_explicit_solution:
        return False
    if "EQUIL" in nrwo:
        tokens = nrwo.split()
        if not tokens or tokens[0] != "EQUIL":
            return False
        kwr.equil = True
        modified_deck.append("--EQUIL --pycopm explicit initialization")
        return True
    if not kwr.equil:
        return False
    tokens = nrwo.split()
    if tokens:
        if tokens[0].startswith("--") or tokens[0][0].isdigit():
            modified_deck.append("--" + nrwo)
        else:
            _append_explicit_solution_includes(dck, modified_deck)
            modified_deck.append(tokens[0])
            kwr.equil = False
    return True


def _append_explicit_solution_includes(
    dck: ConfigViaDeck, modified_deck: list[str]
) -> None:
    """Append include statements for the explicit solution properties."""
    for property_name in dck.solution_keywords:
        modified_deck.append("INCLUDE")
        modified_deck.append(f"'{dck.include_prefix}{property_name.upper()}.INC' /\n")


def _handle_grid_props(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Replace GRID properties and preserve supported GRID-section keywords."""
    if nrwo == "GRID" and not kwr.grid:
        kwr.grid = True
        modified_deck.append(nrwo)
        if len(modified_deck) > 1 and modified_deck[-2].startswith("---"):
            modified_deck.append(modified_deck[-2])
        modified_deck.append("INIT")
        for property_name in (
            dck.base_keywords + dck.grids_keywords + dck.multipliers_keywords
        ):
            modified_deck.append("INCLUDE")
            modified_deck.append(
                f"'{dck.include_prefix}{property_name.upper()}.INC' /\n"
            )
        return True
    if not kwr.grid:
        return False
    if _handle_fault(dck, kwr, modified_deck, nrwo):
        return True
    if _handle_mapaxes(kwr, modified_deck, nrwo):
        return True
    if _handle_aqunum(dck, kwr, modified_deck, nrwo):
        return True
    if _handle_aqucon(dck, kwr, modified_deck, nrwo):
        return True
    if _handle_aquancon(dck, kwr, modified_deck, nrwo):
        return True
    if _handle_bccon(dck, kwr, modified_deck, nrwo):
        return True
    if nrwo == "EDIT":
        kwr.has_edit = True
        if kwr.separator:
            modified_deck.append(kwr.separator)
        modified_deck.append(nrwo)
        if kwr.separator:
            modified_deck.append(kwr.separator)
    if dck.transmissibility_coarsening_method == 0:
        if _handle_pinch(kwr, modified_deck, nrwo):
            return True
        if _handle_multregt(kwr, modified_deck, nrwo):
            return True
        if _handle_multflt(kwr, modified_deck, nrwo):
            return True
        if nrwo == "EDIT":
            kwr.process_edit = True
            modified_deck.append("INCLUDE")
            modified_deck.append(f"'{dck.include_prefix}PORV.INC' /\n")
    if nrwo == "PROPS":
        kwr.grid = False
        if not kwr.process_edit:
            if not kwr.has_edit:
                if kwr.separator:
                    modified_deck.append(kwr.separator)
                modified_deck.append("EDIT")
                if kwr.separator:
                    modified_deck.append(kwr.separator)
            modified_deck.append("INCLUDE")
            modified_deck.append(f"'{dck.include_prefix}PORV.INC' /\n")
            if dck.transmissibility_coarsening_method > 0:
                for property_name in ("tranx", "trany", "tranz"):
                    modified_deck.append("INCLUDE")
                    modified_deck.append(
                        f"'{dck.include_prefix}{property_name.upper()}.INC' /\n"
                    )
    elif kwr.process_edit or (
        kwr.has_edit and (dck.refinement_enabled or dck.vicinity_specification)
    ):
        if _handle_editnnc(dck, kwr, modified_deck, nrwo):
            return True
        if _handle_multiply(dck, kwr, modified_deck, nrwo):
            return True
    else:
        return True
    return False


def _handle_aqunum(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update AQUNUM grid indices for the modified grid."""
    if nrwo == "AQUNUM":
        kwr.aqunum = True
        modified_deck.append(nrwo)
        return True
    if not kwr.aqunum:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        modified_deck.append(nrwo)
        kwr.aqunum = False
    if len(tokens) > 3 and not tokens[0].startswith("--"):
        source_i = int(tokens[1])
        source_j = int(tokens[2])
        source_k = int(tokens[3])
        if dck.vicinity_specification and (
            dck.original_to_output_i[source_i]
            * dck.original_to_output_j[source_j]
            * dck.original_to_output_k[source_k]
            == 0
        ):
            return True
        tokens[1] = str(dck.original_to_output_i[source_i])
        tokens[2] = str(dck.original_to_output_j[source_j])
        tokens[3] = str(dck.original_to_output_k[source_k])
        modified_deck.append(" ".join(tokens))
        return True
    return False


def _handle_aquancon(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update AQUANCON grid-index ranges for the modified grid."""
    if nrwo == "AQUANCON":
        kwr.aquancon = True
        modified_deck.append(nrwo)
        return True
    if not kwr.aquancon:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        modified_deck.append(nrwo)
        kwr.aquancon = False
        return True
    if len(tokens) <= 7 or tokens[0].startswith("--"):
        return False
    source_i1 = int(tokens[1])
    source_i2 = int(tokens[2])
    source_j1 = int(tokens[3])
    source_j2 = int(tokens[4])
    source_k1 = int(tokens[5])
    source_k2 = int(tokens[6])
    if dck.refinement_enabled:
        direction = tokens[7]
        expanded_tokens = tokens.copy()
        mapped_k1 = int(dck.original_to_first_refined_k[source_k1])
        mapped_k2 = int(dck.original_to_last_refined_k[source_k2])
        expanded_tokens[5] = str(mapped_k1)
        expanded_tokens[6] = str(mapped_k2)
        if direction in {"I", "X"}:
            mapped_i = int(dck.original_to_last_refined_i[source_i1])
            expanded_tokens[1] = str(mapped_i)
            expanded_tokens[2] = str(mapped_i)
            mapped_j1 = int(dck.original_to_first_refined_j[source_j1])
            mapped_j2 = int(dck.original_to_last_refined_j[source_j2])
            for mapped_j in range(mapped_j1, mapped_j2 + 1):
                expanded_tokens[3] = str(mapped_j)
                expanded_tokens[4] = str(mapped_j)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"I-", "X-"}:
            mapped_i = int(dck.original_to_first_refined_i[source_i1])
            expanded_tokens[1] = str(mapped_i)
            expanded_tokens[2] = str(mapped_i)
            mapped_j1 = int(dck.original_to_first_refined_j[source_j1])
            mapped_j2 = int(dck.original_to_last_refined_j[source_j2])
            for mapped_j in range(mapped_j1, mapped_j2 + 1):
                expanded_tokens[3] = str(mapped_j)
                expanded_tokens[4] = str(mapped_j)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"J", "Y"}:
            mapped_j = int(dck.original_to_last_refined_j[source_j1])
            expanded_tokens[3] = str(mapped_j)
            expanded_tokens[4] = str(mapped_j)
            mapped_i1 = int(dck.original_to_first_refined_i[source_i1])
            mapped_i2 = int(dck.original_to_last_refined_i[source_i2])
            for mapped_i in range(mapped_i1, mapped_i2 + 1):
                expanded_tokens[1] = str(mapped_i)
                expanded_tokens[2] = str(mapped_i)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"J-", "Y-"}:
            mapped_j = int(dck.original_to_first_refined_j[source_j1])
            expanded_tokens[3] = str(mapped_j)
            expanded_tokens[4] = str(mapped_j)
            mapped_i1 = int(dck.original_to_first_refined_i[source_i1])
            mapped_i2 = int(dck.original_to_last_refined_i[source_i2])
            for mapped_i in range(mapped_i1, mapped_i2 + 1):
                expanded_tokens[1] = str(mapped_i)
                expanded_tokens[2] = str(mapped_i)
                modified_deck.append(" ".join(expanded_tokens))
        tokens[1] = str(dck.original_to_first_refined_i[source_i1])
        tokens[2] = str(dck.original_to_last_refined_i[source_i2])
        tokens[3] = str(dck.original_to_first_refined_j[source_j1])
        tokens[4] = str(dck.original_to_last_refined_j[source_j2])
        tokens[5] = str(mapped_k1)
        tokens[6] = str(mapped_k2)
        return True
    if dck.vicinity_specification and (
        dck.original_to_output_i[source_i1] == 0
        or dck.original_to_output_i[source_i2] == 0
        or dck.original_to_output_j[source_j1] == 0
        or dck.original_to_output_j[source_j2] == 0
        or dck.original_to_output_k[source_k1] == 0
        or dck.original_to_output_k[source_k2] == 0
    ):
        return True
    tokens[1] = str(dck.original_to_output_i[source_i1])
    tokens[2] = str(dck.original_to_output_i[source_i2])
    tokens[3] = str(dck.original_to_output_j[source_j1])
    tokens[4] = str(dck.original_to_output_j[source_j2])
    tokens[5] = str(dck.original_to_output_k[source_k1])
    tokens[6] = str(dck.original_to_output_k[source_k2])
    modified_deck.append(" ".join(tokens))
    return True


def _handle_aqucon(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update AQUCON grid-index ranges for the modified grid."""
    if nrwo == "AQUCON":
        kwr.aqucon = True
        modified_deck.append(nrwo)
        return True
    if not kwr.aqucon:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        modified_deck.append(nrwo)
        kwr.aqucon = False
    if len(tokens) <= 7 or tokens[0].startswith("--"):
        return False
    source_i1 = int(tokens[1])
    source_i2 = int(tokens[2])
    source_j1 = int(tokens[3])
    source_j2 = int(tokens[4])
    source_k1 = int(tokens[5])
    source_k2 = int(tokens[6])
    if dck.refinement_enabled:
        direction = tokens[7]
        expanded_tokens = tokens.copy()
        mapped_k1 = int(dck.original_to_first_refined_k[source_k1])
        mapped_k2 = int(dck.original_to_last_refined_k[source_k2])
        expanded_tokens[5] = str(mapped_k1)
        expanded_tokens[6] = str(mapped_k2)
        if direction in {"I", "X"}:
            mapped_i = int(dck.original_to_last_refined_i[source_i1])
            expanded_tokens[1] = str(mapped_i)
            expanded_tokens[2] = str(mapped_i)
            mapped_j1 = int(dck.original_to_first_refined_j[source_j1])
            mapped_j2 = int(dck.original_to_last_refined_j[source_j2])
            for mapped_j in range(mapped_j1, mapped_j2 + 1):
                expanded_tokens[3] = str(mapped_j)
                expanded_tokens[4] = str(mapped_j)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"I-", "X-"}:
            mapped_i = int(dck.original_to_first_refined_i[source_i1])
            expanded_tokens[1] = str(mapped_i)
            expanded_tokens[2] = str(mapped_i)
            mapped_j1 = int(dck.original_to_first_refined_j[source_j1])
            mapped_j2 = int(dck.original_to_last_refined_j[source_j2])
            for mapped_j in range(mapped_j1, mapped_j2 + 1):
                expanded_tokens[3] = str(mapped_j)
                expanded_tokens[4] = str(mapped_j)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"J", "Y"}:
            mapped_j = int(dck.original_to_last_refined_j[source_j1])
            expanded_tokens[3] = str(mapped_j)
            expanded_tokens[4] = str(mapped_j)
            mapped_i1 = int(dck.original_to_first_refined_i[source_i1])
            mapped_i2 = int(dck.original_to_last_refined_i[source_i2])
            for mapped_i in range(mapped_i1, mapped_i2 + 1):
                expanded_tokens[1] = str(mapped_i)
                expanded_tokens[2] = str(mapped_i)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"J-", "Y-"}:
            mapped_j = int(dck.original_to_first_refined_j[source_j1])
            expanded_tokens[3] = str(mapped_j)
            expanded_tokens[4] = str(mapped_j)
            mapped_i1 = int(dck.original_to_first_refined_i[source_i1])
            mapped_i2 = int(dck.original_to_last_refined_i[source_i2])
            for mapped_i in range(mapped_i1, mapped_i2 + 1):
                expanded_tokens[1] = str(mapped_i)
                expanded_tokens[2] = str(mapped_i)
                modified_deck.append(" ".join(expanded_tokens))
        tokens[1] = str(dck.original_to_first_refined_i[source_i1])
        tokens[2] = str(dck.original_to_last_refined_i[source_i2])
        tokens[3] = str(dck.original_to_first_refined_j[source_j1])
        tokens[4] = str(dck.original_to_last_refined_j[source_j2])
        tokens[5] = str(mapped_k1)
        tokens[6] = str(mapped_k2)
        return True
    if dck.vicinity_specification and (
        dck.original_to_output_i[source_i1] == 0
        or dck.original_to_output_i[source_i2] == 0
        or dck.original_to_output_j[source_j1] == 0
        or dck.original_to_output_j[source_j2] == 0
        or dck.original_to_output_k[source_k1] == 0
        or dck.original_to_output_k[source_k2] == 0
    ):
        return True
    tokens[1] = str(dck.original_to_output_i[source_i1])
    tokens[2] = str(dck.original_to_output_i[source_i2])
    tokens[3] = str(dck.original_to_output_j[source_j1])
    tokens[4] = str(dck.original_to_output_j[source_j2])
    tokens[5] = str(dck.original_to_output_k[source_k1])
    tokens[6] = str(dck.original_to_output_k[source_k2])
    modified_deck.append(" ".join(tokens))
    return True


def _handle_multflt(kwr: _ParserState, modified_deck: list[str], nrwo: str) -> bool:
    """Preserve fault multiplier records from the input deck."""
    if "MULTFLT" in nrwo:
        tokens = nrwo.split()
        if not tokens or tokens[0] != "MULTFLT":
            return False
        kwr.multflt = True
        modified_deck.append(tokens[0])
        return True
    if not kwr.multflt:
        return False
    tokens = nrwo.split()
    if tokens:
        modified_deck.append(nrwo)
        if tokens[0] == "/":
            kwr.multflt = False
    return True


def _handle_mapaxes(kwr: _ParserState, modified_deck: list[str], nrwo: str) -> bool:
    """Preserve MAPAXES so the generated grids retain the same map view."""
    if "MAPAXES" in nrwo:
        tokens = nrwo.split()
        if not tokens or tokens[0] != "MAPAXES":
            return False
        kwr.mapaxes = True
        modified_deck.append(tokens[0])
        return True
    if not kwr.mapaxes:
        return False
    tokens = nrwo.split()
    if tokens:
        modified_deck.append(nrwo)
        if tokens[-1] == "/" or tokens[0] == "/":
            kwr.mapaxes = False
    return True


def _handle_pinch(kwr: _ParserState, modified_deck: list[str], nrwo: str) -> bool:
    """Preserve PINCH records from the input deck."""
    if "PINCH" in nrwo:
        tokens = nrwo.split()
        if not tokens or tokens[0] != "PINCH":
            return False
        kwr.pinch = True
        modified_deck.append(tokens[0])
        return True
    if not kwr.pinch:
        return False
    tokens = nrwo.split()
    if tokens and not tokens[0].startswith("--"):
        modified_deck.append(nrwo)
        if "/" in tokens[0] or "/" in tokens[-1]:
            kwr.pinch = False
    return True


def _handle_multregt(kwr: _ParserState, modified_deck: list[str], nrwo: str) -> bool:
    """Preserve MULTREGT records from the GRID section."""
    if "MULTREGT" in nrwo and "/" not in nrwo:
        tokens = nrwo.split()
        if not tokens or tokens[0] != "MULTREGT":
            return False
        kwr.multregt = True
        modified_deck.append(tokens[0])
        return True
    if not kwr.multregt:
        return False
    tokens = nrwo.split()
    if tokens:
        modified_deck.append(nrwo)
        if tokens[0] == "/":
            kwr.multregt = False
    return True


def _handle_bccon(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update BCCON grid-index ranges for the modified grid."""
    if nrwo == "BCCON":
        kwr.bccon = True
        modified_deck.append(nrwo)
        return True
    if not kwr.bccon:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        modified_deck.append(nrwo)
        kwr.bccon = False
        return True
    if len(tokens) <= 6 or tokens[0].startswith("--"):
        return False
    source_i1 = int(tokens[1])
    source_i2 = int(tokens[2])
    source_j1 = int(tokens[3])
    source_j2 = int(tokens[4])
    source_k1 = int(tokens[5])
    source_k2 = int(tokens[6])
    if dck.refinement_enabled:
        tokens[1] = str(dck.original_to_first_refined_i[source_i1])
        tokens[2] = str(dck.original_to_last_refined_i[source_i2])
        tokens[3] = str(dck.original_to_first_refined_j[source_j1])
        tokens[4] = str(dck.original_to_last_refined_j[source_j2])
        tokens[5] = str(dck.original_to_first_refined_k[source_k1])
        tokens[6] = str(dck.original_to_last_refined_k[source_k2])
    else:
        if dck.vicinity_specification and (
            dck.original_to_output_i[source_i1] == 0
            or dck.original_to_output_i[source_i2] == 0
            or dck.original_to_output_j[source_j1] == 0
            or dck.original_to_output_j[source_j2] == 0
            or dck.original_to_output_k[source_k1] == 0
            or dck.original_to_output_k[source_k2] == 0
        ):
            return True
        tokens[1] = str(dck.original_to_output_i[source_i1])
        tokens[2] = str(dck.original_to_output_i[source_i2])
        tokens[3] = str(dck.original_to_output_j[source_j1])
        tokens[4] = str(dck.original_to_output_j[source_j2])
        tokens[5] = str(dck.original_to_output_k[source_k1])
        tokens[6] = str(dck.original_to_output_k[source_k2])
    modified_deck.append(" ".join(tokens))
    return True


def _handle_multiply(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update MULTIPLY grid-index ranges for the modified grid."""
    if nrwo == "MULTIPLY":
        kwr.multiply = True
        modified_deck.append(nrwo)
        return True
    if kwr.multiply:
        tokens = nrwo.split()
        if tokens and tokens[0] == "/":
            modified_deck.append(nrwo)
            kwr.multiply = False
        if len(tokens) > 7 and not tokens[0].startswith("--"):
            source_i1 = int(tokens[2])
            source_i2 = int(tokens[3])
            source_j1 = int(tokens[4])
            source_j2 = int(tokens[5])
            source_k1 = int(tokens[6])
            source_k2 = int(tokens[7])
            if dck.refinement_enabled:
                tokens[2] = str(dck.original_to_first_refined_i[source_i1])
                tokens[3] = str(dck.original_to_last_refined_i[source_i2])
                tokens[4] = str(dck.original_to_first_refined_j[source_j1])
                tokens[5] = str(dck.original_to_last_refined_j[source_j2])
                tokens[6] = str(dck.original_to_first_refined_k[source_k1])
                tokens[7] = str(dck.original_to_last_refined_k[source_k2])
            else:
                if dck.vicinity_specification and (
                    dck.original_to_output_i[source_i1] == 0
                    or dck.original_to_output_i[source_i2] == 0
                    or dck.original_to_output_j[source_j1] == 0
                    or dck.original_to_output_j[source_j2] == 0
                    or dck.original_to_output_k[source_k1] == 0
                    or dck.original_to_output_k[source_k2] == 0
                ):
                    return True
                tokens[2] = str(dck.original_to_output_i[source_i1])
                tokens[3] = str(dck.original_to_output_i[source_i2])
                tokens[4] = str(dck.original_to_output_j[source_j1])
                tokens[5] = str(dck.original_to_output_j[source_j2])
                tokens[6] = str(dck.original_to_output_k[source_k1])
                tokens[7] = str(dck.original_to_output_k[source_k2])
            modified_deck.append(" ".join(tokens))
            return True
    return True


def _handle_editnnc(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update EDITNNC grid indices for the modified grid."""
    if nrwo == "EDITNNC":
        kwr.editnnc = True
        modified_deck.append(nrwo)
        return True
    if not kwr.editnnc:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        modified_deck.append(nrwo)
        kwr.editnnc = False
    if len(tokens) <= 5 or tokens[0].startswith("--"):
        return False
    source_i1 = int(tokens[0])
    source_j1 = int(tokens[1])
    source_k1 = int(tokens[2])
    source_i2 = int(tokens[3])
    source_j2 = int(tokens[4])
    source_k2 = int(tokens[5])
    if dck.refinement_enabled:
        tokens[0] = str(dck.original_to_first_refined_i[source_i1])
        tokens[1] = str(dck.original_to_first_refined_j[source_j1])
        tokens[2] = str(dck.original_to_first_refined_k[source_k1])
        tokens[3] = str(dck.original_to_last_refined_i[source_i2])
        tokens[4] = str(dck.original_to_last_refined_j[source_j2])
        tokens[5] = str(dck.original_to_last_refined_k[source_k2])
    else:
        if dck.vicinity_specification and (
            dck.original_to_output_i[source_i1] == 0
            or dck.original_to_output_j[source_j1] == 0
            or dck.original_to_output_k[source_k1] == 0
            or dck.original_to_output_i[source_i2] == 0
            or dck.original_to_output_j[source_j2] == 0
            or dck.original_to_output_k[source_k2] == 0
        ):
            return True
        tokens[0] = str(dck.original_to_output_i[source_i1])
        tokens[1] = str(dck.original_to_output_j[source_j1])
        tokens[2] = str(dck.original_to_output_k[source_k1])
        tokens[3] = str(dck.original_to_output_i[source_i2])
        tokens[4] = str(dck.original_to_output_j[source_j2])
        tokens[5] = str(dck.original_to_output_k[source_k2])
    modified_deck.append(" ".join(tokens))
    return True


def _handle_fault(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update FAULTS grid-index ranges for the modified grid."""
    if nrwo == "FAULTS":
        kwr.faults = True
        modified_deck.append(nrwo)
        return True
    if not kwr.faults:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        modified_deck.append(nrwo)
        kwr.faults = False
    if len(tokens) <= 7 or tokens[0].startswith("--"):
        return False
    source_i1 = int(tokens[1])
    source_i2 = int(tokens[2])
    source_j1 = int(tokens[3])
    source_j2 = int(tokens[4])
    source_k1 = int(tokens[5])
    source_k2 = int(tokens[6])
    if dck.refinement_enabled:
        direction = tokens[7]
        expanded_tokens = tokens.copy()
        mapped_k1 = int(dck.original_to_first_refined_k[source_k1])
        mapped_k2 = int(dck.original_to_last_refined_k[source_k2])
        expanded_tokens[5] = str(mapped_k1)
        expanded_tokens[6] = str(mapped_k2)
        if direction in {"I", "X"}:
            mapped_i = int(dck.original_to_last_refined_i[source_i1])
            mapped_j1 = int(dck.original_to_first_refined_j[source_j1])
            mapped_j2 = int(dck.original_to_last_refined_j[source_j2])
            expanded_tokens[1] = str(mapped_i)
            expanded_tokens[2] = str(mapped_i)
            for mapped_j in range(mapped_j1, mapped_j2 + 1):
                expanded_tokens[3] = str(mapped_j)
                expanded_tokens[4] = str(mapped_j)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"I-", "X-"}:
            mapped_i = int(dck.original_to_first_refined_i[source_i1])
            mapped_j1 = int(dck.original_to_first_refined_j[source_j1])
            mapped_j2 = int(dck.original_to_last_refined_j[source_j2])
            expanded_tokens[1] = str(mapped_i)
            expanded_tokens[2] = str(mapped_i)
            for mapped_j in range(mapped_j1, mapped_j2 + 1):
                expanded_tokens[3] = str(mapped_j)
                expanded_tokens[4] = str(mapped_j)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"J", "Y"}:
            mapped_j = int(dck.original_to_last_refined_j[source_j1])
            mapped_i1 = int(dck.original_to_first_refined_i[source_i1])
            mapped_i2 = int(dck.original_to_last_refined_i[source_i2])
            expanded_tokens[3] = str(mapped_j)
            expanded_tokens[4] = str(mapped_j)
            for mapped_i in range(mapped_i1, mapped_i2 + 1):
                expanded_tokens[1] = str(mapped_i)
                expanded_tokens[2] = str(mapped_i)
                modified_deck.append(" ".join(expanded_tokens))
        elif direction in {"J-", "Y-"}:
            mapped_j = int(dck.original_to_first_refined_j[source_j1])
            mapped_i1 = int(dck.original_to_first_refined_i[source_i1])
            mapped_i2 = int(dck.original_to_last_refined_i[source_i2])
            expanded_tokens[3] = str(mapped_j)
            expanded_tokens[4] = str(mapped_j)
            for mapped_i in range(mapped_i1, mapped_i2 + 1):
                expanded_tokens[1] = str(mapped_i)
                expanded_tokens[2] = str(mapped_i)
                modified_deck.append(" ".join(expanded_tokens))
        tokens[1] = str(dck.original_to_first_refined_i[source_i1])
        tokens[2] = str(dck.original_to_last_refined_i[source_i2])
        tokens[3] = str(dck.original_to_first_refined_j[source_j1])
        tokens[4] = str(dck.original_to_last_refined_j[source_j2])
        tokens[5] = str(mapped_k1)
        tokens[6] = str(mapped_k2)
        return True
    if dck.vicinity_specification and (
        dck.original_to_output_i[source_i1] == 0
        or dck.original_to_output_i[source_i2] == 0
        or dck.original_to_output_j[source_j1] == 0
        or dck.original_to_output_j[source_j2] == 0
        or dck.original_to_output_k[source_k1] == 0
        or dck.original_to_output_k[source_k2] == 0
    ):
        return True
    tokens[1] = str(dck.original_to_output_i[source_i1])
    tokens[2] = str(dck.original_to_output_i[source_i2])
    tokens[3] = str(dck.original_to_output_j[source_j1])
    tokens[4] = str(dck.original_to_output_j[source_j2])
    tokens[5] = str(dck.original_to_output_k[source_k1])
    tokens[6] = str(dck.original_to_output_k[source_k2])
    modified_deck.append(" ".join(tokens))
    return True


def _handle_welsegs(kwr: _ParserState, modified_deck: list[str], nrwo: str) -> bool:
    """Filter WELSEGS records by wells retained in the submodel."""
    if nrwo == "WELSEGS":
        kwr.welsegs = True
        modified_deck.append(nrwo)
        return True
    if not kwr.welsegs:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        kwr.welsegs = False
        if kwr.skip_block:
            kwr.skip_block = False
            return True
    if len(tokens) > 1:
        if not tokens[0].startswith("--") and modified_deck[-1] == "WELSEGS":
            well_name = tokens[0].replace("'", "")
            if (
                well_name not in kwr.retained_wells
                or well_name not in kwr.segmented_wells
            ):
                del modified_deck[-1]
                if modified_deck and modified_deck[-1] == "WELSEGS":
                    del modified_deck[-1]
                kwr.skip_block = True
                return True
        elif not tokens[0].startswith("--") and not kwr.skip_block:
            modified_deck.append(nrwo)
            return True
        else:
            return True
    elif kwr.skip_block:
        return True
    return False


def _handle_compsegs(kwr: _ParserState, modified_deck: list[str], nrwo: str) -> bool:
    """Filter COMPSEGS records by wells retained in the submodel."""
    if nrwo == "COMPSEGS":
        kwr.compsegs = True
        modified_deck.append(nrwo)
        return True
    if not kwr.compsegs:
        return False
    tokens = nrwo.split()
    if tokens and tokens[0] == "/":
        kwr.compsegs = False
        if kwr.skip_block:
            kwr.skip_block = False
            return True
    if len(tokens) > 1:
        if not tokens[0].startswith("--") and modified_deck[-1] == "COMPSEGS":
            well_name = tokens[0].replace("'", "")
            if well_name not in kwr.retained_wells:
                del modified_deck[-1]
                if modified_deck and modified_deck[-1] == "COMPSEGS":
                    del modified_deck[-1]
                kwr.skip_block = True
                return True
        elif not kwr.skip_block:
            modified_deck.append(nrwo)
            return True
        else:
            return True
    elif kwr.skip_block:
        return True
    return False


def _handle_segmented_wells(
    dck: ConfigViaDeck,
    kwr: _ParserState,
    modified_deck: list[str],
    nrwo: str,
    wellcind: list,
) -> bool:
    """Update COMPDAT, COMPSEGS, and COMPLUMP records for the modified grid."""
    if nrwo == "COMPSEGS":
        kwr.compsegs = True
        modified_deck.append(nrwo)
        return True
    if kwr.compdat:
        tokens = nrwo.split()
        if tokens and tokens[0] == "/":
            kwr.previous_completion = []
            kwr.compdat = False
        if len(tokens) > 4 and not tokens[0].startswith("--"):
            well_name = tokens[0].replace("'", "")
            source_i = int(tokens[1])
            source_j = int(tokens[2])
            source_k1 = int(tokens[3])
            source_k2 = int(tokens[4])
            if dck.vicinity_specification and (
                well_name not in kwr.retained_wells
                or dck.original_to_output_i[source_i]
                * dck.original_to_output_j[source_j]
                * dck.original_to_output_k[source_k1]
                * dck.original_to_output_k[source_k2]
                == 0
            ):
                return True
            if (
                dck.completion_removal_level > 0
                and len(tokens) > 7
                and tokens[7] != "/"
            ):
                tokens[7] = "1*"
            if (
                dck.completion_removal_level > 0
                and len(tokens) > 9
                and tokens[9] not in {"1*", "2*", "3*", "/"}
            ):
                tokens[9] = "1*"
            if (
                dck.completion_removal_level > 1
                and len(tokens) > 12
                and tokens[-2] != "/"
            ):
                tokens[-2] = ""
            tokens[1] = str(dck.original_to_output_i[source_i])
            tokens[2] = str(dck.original_to_output_j[source_j])
            if dck.refinement_enabled:
                if kwr.previous_completion:
                    previous_tokens = kwr.previous_completion
                    previous_well = previous_tokens[0].replace("'", "")
                    previous_source_i = int(previous_tokens[1])
                    previous_source_j = int(previous_tokens[2])
                    previous_source_k1 = int(previous_tokens[3])
                    previous_source_k2 = int(previous_tokens[4])
                    previous_i = int(dck.original_to_output_i[previous_source_i])
                    previous_j = int(dck.original_to_output_j[previous_source_j])
                    if (
                        well_name == previous_well
                        and previous_well not in kwr.compsegs_wells
                        and (
                            tokens[1] != str(previous_i) or tokens[2] != str(previous_j)
                        )
                    ):
                        tokens[3] = str(dck.original_to_output_k[source_k1])
                        tokens[4] = str(dck.original_to_output_k[source_k2])
                        current_completion = tokens.copy()
                        previous_completion = tokens.copy()
                        previous_completion[3] = str(
                            dck.original_to_output_k[previous_source_k1]
                        )
                        previous_completion[4] = str(
                            dck.original_to_output_k[previous_source_k2]
                        )
                        if int(tokens[1]) != previous_i:
                            difference = int(tokens[1]) - previous_i
                            for offset in range(abs(difference) - 1):
                                intermediate_i = previous_i + int(
                                    (offset + 1) * difference / abs(difference)
                                )
                                current_completion[1] = str(intermediate_i)
                                previous_completion[1] = str(intermediate_i)
                                if offset < (abs(difference) - 1) / 2:
                                    modified_deck.append(" ".join(previous_completion))
                                else:
                                    modified_deck.append(" ".join(current_completion))
                        elif int(tokens[2]) != previous_j:
                            difference = int(tokens[2]) - previous_j
                            for offset in range(abs(difference) - 1):
                                intermediate_j = previous_j + int(
                                    (offset + 1) * difference / abs(difference)
                                )
                                current_completion[2] = str(intermediate_j)
                                previous_completion[2] = str(intermediate_j)
                                if offset < (abs(difference) - 1) / 2:
                                    modified_deck.append(" ".join(previous_completion))
                                else:
                                    modified_deck.append(" ".join(current_completion))
                    elif (
                        well_name == previous_well
                        and previous_well not in kwr.compsegs_wells
                        and previous_well in kwr.segmented_wells
                        and tokens[1] == str(previous_i)
                        and tokens[2] == str(previous_j)
                        and dck.original_to_output_k[source_k1]
                        != dck.original_to_output_k[previous_source_k1]
                    ):
                        mapped_k = int(dck.original_to_output_k[source_k1])
                        previous_k = int(dck.original_to_output_k[previous_source_k1])
                        if previous_k < mapped_k:
                            k_values = range(previous_k, mapped_k)
                        else:
                            k_values = range(mapped_k, previous_k)
                        for mapped_k_value in k_values:
                            tokens[3] = str(mapped_k_value + 1)
                            tokens[4] = str(mapped_k_value + 1)
                            modified_deck.append(" ".join(tokens))
                        kwr.previous_completion = nrwo.split()
                        return True
                    elif well_name in kwr.segmented_wells + kwr.compsegs_wells:
                        tokens[3] = str(dck.original_to_output_k[source_k1])
                        tokens[4] = str(dck.original_to_output_k[source_k2])
                    else:
                        tokens[3] = str(dck.original_to_first_refined_k[source_k1])
                        tokens[4] = str(dck.original_to_last_refined_k[source_k2])
                elif well_name in kwr.segmented_wells + kwr.compsegs_wells:
                    tokens[3] = str(dck.original_to_output_k[source_k1])
                    tokens[4] = str(dck.original_to_output_k[source_k2])
                else:
                    tokens[3] = str(dck.original_to_first_refined_k[source_k1])
                    tokens[4] = str(dck.original_to_last_refined_k[source_k2])
            else:
                tokens[3] = str(dck.original_to_output_k[source_k1])
                tokens[4] = str(dck.original_to_output_k[source_k2])
            if dck.coarsening_enabled and dck.transmissibility_coarsening_method > 0:
                completion_i = int(tokens[1])
                completion_j = int(tokens[2])
                for completion_k in range(int(tokens[3]), int(tokens[4]) + 1):
                    cell_index = (
                        completion_i
                        - 1
                        + (completion_j - 1) * dck.output_nx
                        + (completion_k - 1) * dck.output_nx * dck.output_ny
                    )
                    wellcind.append(cell_index)
            modified_deck.append(" ".join(tokens))
            kwr.previous_completion = nrwo.split()
            return True
    if kwr.compsegs:
        tokens = nrwo.split()
        if tokens and tokens[0] == "/":
            kwr.compsegs = False
            if modified_deck[-1].split()[0] in kwr.completion_wells:
                del modified_deck[-1]
                del modified_deck[-1]
                return True
        if (
            len(tokens) > 1
            and not tokens[0].startswith("--")
            and modified_deck[-1].split()[0] == "COMPSEGS"
            and dck.vicinity_specification
        ):
            well_name = tokens[0].replace("'", "")
            if (
                well_name not in kwr.retained_wells
                or well_name not in kwr.segmented_wells
            ):
                del modified_deck[-1]
                del modified_deck[-1]
                return True
        if len(tokens) > 2:
            if not tokens[0].startswith("--"):
                if dck.vicinity_specification:
                    well_name = tokens[0].replace("'", "")
                    if (well_name not in kwr.retained_wells and len(tokens) < 4) or (
                        dck.original_to_output_i[int(tokens[0])]
                        * dck.original_to_output_j[int(tokens[1])]
                        * dck.original_to_output_k[int(tokens[2])]
                        == 0
                    ):
                        return True
                    tokens[0] = str(dck.original_to_output_i[int(tokens[0])])
                    tokens[1] = str(dck.original_to_output_j[int(tokens[1])])
                    tokens[2] = str(dck.original_to_output_k[int(tokens[2])])
                    modified_deck.append(" ".join(tokens))
                    return True
                tokens[0] = str(dck.original_to_output_i[int(tokens[0])])
                tokens[1] = str(dck.original_to_output_j[int(tokens[1])])
                tokens[2] = str(dck.original_to_output_k[int(tokens[2])])
                modified_deck.append(" ".join(tokens))
                return True
            return True
    if kwr.complump:
        tokens = nrwo.split()
        if tokens and tokens[0] == "/":
            kwr.complump = False
            if modified_deck[-1].split()[0] in kwr.completion_wells:
                del modified_deck[-1]
                del modified_deck[-1]
                return True
        if (
            len(tokens) > 1
            and not tokens[0].startswith("--")
            and modified_deck[-1].split()[0] == "COMPLUMP"
            and dck.vicinity_specification
        ):
            well_name = tokens[0].replace("'", "")
            if (
                well_name not in kwr.retained_wells
                or well_name not in kwr.segmented_wells
            ):
                del modified_deck[-1]
                del modified_deck[-1]
                return True
        if len(tokens) > 2:
            if not tokens[0].startswith("--"):
                original_tokens = tokens.copy()
                position_offset = 0
                for position, value in enumerate(original_tokens):
                    if "*" in value:
                        tokens.pop(position + position_offset)
                        repeat_count = int(value[0])
                        for _ in range(repeat_count):
                            tokens.insert(position + position_offset, "1*")
                        position_offset += repeat_count - 1
                if dck.vicinity_specification:
                    well_name = tokens[0].replace("'", "")
                    for value, axis_name in zip(
                        tokens[1:5], ("i", "j", "k", "k"), strict=True
                    ):
                        if (
                            "*" not in value
                            and getattr(dck, f"{axis_name}c")[int(value)] == 0
                        ):
                            return True
                    if well_name not in kwr.retained_wells:
                        return True
                    for position, axis_name in zip(
                        range(1, 5), ("i", "j", "k", "k"), strict=True
                    ):
                        if "*" not in tokens[position]:
                            source_index = int(tokens[position])
                            tokens[position] = str(
                                getattr(dck, f"{axis_name}c")[source_index]
                            )
                    modified_deck.append(" ".join(tokens))
                    return True
                for position, axis_name in zip(
                    range(1, 5), ("i", "j", "k", "k"), strict=True
                ):
                    if "*" not in tokens[position]:
                        source_index = int(tokens[position])
                        tokens[position] = str(
                            getattr(dck, f"{axis_name}c")[source_index]
                        )
                modified_deck.append(" ".join(tokens))
                return True
            return True
    return False


def _handle_wells(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str, hv: bool
) -> bool:
    """Update well-head grid indices and activate completion handlers."""
    if nrwo == "WELSPECS":
        kwr.welspecs = True
        modified_deck.append(nrwo)
        return True
    if kwr.welspecs:
        tokens = nrwo.split()
        if len(tokens) > 3 and not tokens[0].startswith("--"):
            well_name = tokens[0].replace("'", "")
            source_i = int(tokens[2])
            source_j = int(tokens[3])
            if dck.vicinity_specification:
                if well_name not in kwr.retained_wells:
                    return True
                if hv:
                    mapped_i = int(dck.original_to_output_i[source_i])
                    if mapped_i == 0:
                        for offset in range(dck.output_nx):
                            lower_i = source_i - offset
                            upper_i = source_i + offset
                            if (
                                lower_i >= 0
                                and int(dck.original_to_output_i[lower_i]) > 0
                            ):
                                mapped_i = int(dck.original_to_output_i[lower_i])
                                break
                            if (
                                upper_i < len(dck.original_to_output_i)
                                and int(dck.original_to_output_i[upper_i]) > 0
                            ):
                                mapped_i = int(dck.original_to_output_i[upper_i])
                                break
                    if mapped_i > 0:
                        tokens[2] = str(mapped_i)
                    mapped_j = int(dck.original_to_output_j[source_j])
                    if mapped_j == 0:
                        for offset in range(dck.output_ny):
                            lower_j = source_j - offset
                            upper_j = source_j + offset
                            if (
                                lower_j >= 0
                                and int(dck.original_to_output_j[lower_j]) > 0
                            ):
                                mapped_j = int(dck.original_to_output_j[lower_j])
                                break
                            if (
                                upper_j < len(dck.original_to_output_j)
                                and int(dck.original_to_output_j[upper_j]) > 0
                            ):
                                mapped_j = int(dck.original_to_output_j[upper_j])
                                break
                    if mapped_j > 0:
                        tokens[3] = str(mapped_j)
                    modified_deck.append(" ".join(tokens))
                    return True
                if (
                    dck.original_to_output_i[source_i]
                    * dck.original_to_output_j[source_j]
                    == 0
                ):
                    tokens[2] = "1"
                    tokens[3] = "1"
                    modified_deck.append(" ".join(tokens))
                    return True
            tokens[2] = str(dck.original_to_output_i[source_i])
            tokens[3] = str(dck.original_to_output_j[source_j])
            modified_deck.append(" ".join(tokens))
            return True
        if tokens and tokens[0] == "/":
            kwr.welspecs = False
    if nrwo == "COMPDAT":
        kwr.compdat = True
        modified_deck.append(nrwo)
        return True
    if nrwo == "COMPLUMP":
        kwr.complump = True
        modified_deck.append(nrwo)
        return True
    return False


def _handle_source(
    dck: ConfigViaDeck, kwr: _ParserState, modified_deck: list[str], nrwo: str
) -> bool:
    """Update SOURCE grid indices for the modified grid."""
    if nrwo == "SOURCE":
        kwr.source = True
        modified_deck.append(nrwo)
        return True
    if not kwr.source:
        return False
    tokens = nrwo.split()
    if len(tokens) > 2 and not tokens[0].startswith("--"):
        source_i = int(tokens[0])
        source_j = int(tokens[1])
        source_k = int(tokens[2])
        if dck.vicinity_specification and (
            dck.original_to_output_i[source_i]
            * dck.original_to_output_j[source_j]
            * dck.original_to_output_k[source_k]
            == 0
        ):
            return True
        tokens[0] = str(dck.original_to_output_i[source_i])
        tokens[1] = str(dck.original_to_output_j[source_j])
        tokens[2] = str(dck.original_to_output_k[source_k])
        modified_deck.append(" ".join(tokens))
        return True
    if tokens and tokens[0] == "/":
        kwr.source = False
    return False


def _scan_deck_file(
    dck: ConfigViaDeck, file_path: str | Path
) -> tuple[list[str], bool, NDArray]:
    """Scan a deck file for includes and directional multipliers.

    Parameters
    ----------
    dck
        Deck configuration providing the file encoding.
    file_path
        DATA or include file to scan.

    Returns
    -------
    includes, has_main_multflt, multipliers
        Resolved include paths, whether the main deck contains ``MULTFLT``, and
        flags for ``MULTX``, ``MULTX-``, ``MULTY``, ``MULTY-``, ``MULTZ``, and
        ``MULTZ-``."""
    path = Path(file_path)
    includes: list[str] = []
    include_pending = False
    maindeckmultflt = False
    mults = np.array([False, False, False, False, False, False])
    is_main_deck = ".DATA" in str(path)
    base_directory = path.resolve().parent
    with path.open("r", encoding=dck.deck_encoding) as file_handle:
        for csv_row in csv.reader(file_handle):
            deck_line = str(csv_row)[2:-2].strip()
            if include_pending:
                include_path = deck_line.split("--", maxsplit=1)[0]
                include_path = include_path.replace(" /", "").rstrip("/").strip()
                include_path = include_path.strip("'\"")
                resolved_include = Path(os.path.normpath(base_directory / include_path))
                if resolved_include.exists():
                    includes.append(str(resolved_include))
                else:
                    print(f"Include not found: {resolved_include}")
                include_pending = False
                continue
            mults = _mark_multiplier_keyword(deck_line, mults)
            if deck_line == "INCLUDE":
                include_pending = True
            if is_main_deck and deck_line == "MULTFLT":
                maindeckmultflt = True
    return includes, maindeckmultflt, mults


def _mark_multiplier_keyword(deck_line: str, mults: NDArray) -> NDArray:
    """Set the corresponding flag if a multiplier keyword is found."""
    keywords = deck_line.split()
    for i, multiplier in enumerate(
        ["multx", "multx-", "multy", "multy-", "multz", "multz-"]
    ):
        keyword = multiplier.upper()
        if deck_line == keyword or (len(keywords) > 1 and keywords[0] == keyword):
            mults[i] = True
            return mults
    return mults


def find_multiplier_keywords(dck: ConfigViaDeck) -> tuple[bool, NDArray]:
    """Find directional multiplier keywords in nested includes.

    At most three levels of included files are scanned.

    Parameters
    ----------
    dck
        Deck configuration identifying the input deck and encoding.

    Returns
    -------
    has_main_multflt, multipliers
        Whether the main deck contains ``MULTFLT`` and directional multiplier
        flags in x, x-, y, y-, z, and z- order."""
    multipliers_values = np.array([False, False, False, False, False, False])
    maindeckmultflt = False
    included_files, multflt, mults = _scan_deck_file(dck, f"{dck.input_deck_name}.DATA")
    maindeckmultflt = maindeckmultflt or multflt
    multipliers_values = multipliers_values | mults
    first_level_includes: list[str] = []
    second_level_includes: list[str] = []
    for included_file in included_files:
        incs, multflt, mults = _scan_deck_file(dck, included_file)
        first_level_includes.extend(incs)
        maindeckmultflt = maindeckmultflt or multflt
        multipliers_values = multipliers_values | mults
    for included_file in first_level_includes:
        incs, multflt, mults = _scan_deck_file(dck, included_file)
        second_level_includes.extend(incs)
        maindeckmultflt = maindeckmultflt or multflt
        multipliers_values = multipliers_values | mults
    for included_file in second_level_includes:
        incs, multflt, mults = _scan_deck_file(dck, included_file)
        maindeckmultflt = maindeckmultflt or multflt
        multipliers_values = multipliers_values | mults
    return maindeckmultflt, multipliers_values
