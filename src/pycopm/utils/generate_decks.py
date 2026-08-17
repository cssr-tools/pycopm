# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,R0801,E1102

"""Coordinate coarsening, refinement, submodel extraction, and grid transformations."""

import argparse
import csv
import subprocess
import sys
from pathlib import Path
from shutil import copy2
from typing import cast

import numpy as np
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid

from pycopm.config.config import ConfigViaDeck
from pycopm.utils.coarsening import (
    CoarseningMaps,
    build_dual_porosity_grid,
    coarsen_corner_point_grid,
    coarsen_properties,
    create_coarsening_maps,
    map_nnc_transmissibilities,
    redistribute_removed_pore_volume,
)
from pycopm.utils.files_writer import (
    write_dual_properties,
    write_grid,
    write_include,
    write_porv,
)
from pycopm.utils.parser_deck import find_multiplier_keywords, process_deck
from pycopm.utils.refinement import (
    RefinementMaps,
    create_refinement_maps,
    refine_grid,
    refine_properties,
)
from pycopm.utils.transformation import (
    transform_grid,
    transform_properties,
)
from pycopm.utils.vicinity import (
    VicinityMaps,
    apply_boundary_pore_volume_correction,
    create_vicinity_maps,
    extract_vicinity_grid,
    map_vicinity_properties,
)


def create_deck(dck: ConfigViaDeck, cmdargs: argparse.Namespace) -> None:
    """Generate a modified OPM deck and its include files.

    The selected workflow can preprocess the input deck, coarsen or refine the
    grid, extract a vicinity submodel, transform coordinates, and optionally run
    a validation dry run.

    Parameters
    ----------
    dck
        Deck configuration populated from command-line arguments.
    cmdargs
        Parsed command arguments used to build coarsening or refinement maps."""
    output_directory = Path(dck.output_directory)
    source_deck = Path(f"{dck.input_deck_path}.DATA")
    if dck.requested_ijk[0]:
        dck.requested_ijk = [int(value) for value in dck.requested_ijk[0].split(",")]
        dck.execution_mode = "deck"
    if not dck.output_deck_name:
        dck.output_deck_name = f"{dck.input_deck_name}_PYCOPM"
    flags_dry_run = (
        "--parsing-strictness=low --check-satfunc-consistency=false "
        "--enable-dry-run=true --output-mode=none"
    )
    output_types = [".INIT", ".EGRID"]
    dry_run_name = f"{dck.input_deck_name}_PREP_PYCOPM_DRYRUN"
    dry_run_deck = output_directory / f"{dry_run_name}.DATA"
    if dck.execution_mode in ("prep", "prep_deck", "all"):
        if dck.write_explicit_solution:
            output_types.append(".UNRST")
            modified_deck = []
            with source_deck.open("r", encoding="utf8") as file_handle:
                for csv_row in csv.reader(file_handle):
                    deck_line = str(csv_row)[2:-2].strip()
                    if deck_line == "SCHEDULE":
                        modified_deck.append(deck_line)
                        modified_deck.append("RPTRST\n'BASIC=2'/\n")
                        modified_deck.append("TSTEP\n1*0.0001/\n")
                        break
                    modified_deck.append(deck_line)
            dry_run_deck.write_text(
                "".join(f"{deck_line}\n" for deck_line in modified_deck),
                encoding="utf8",
            )
            print(
                f"\nTemporal {dry_run_deck.name} from {source_deck} for the initial "
                "run to generate the grid (.EGRID), static (.INIT), and initial "
                "(.UNRST) properties\n"
            )
            subprocess.run(
                [
                    dck.flow_command,
                    dry_run_deck.name,
                    "--output-mode=none",
                    "--parsing-strictness=low",
                    "--enable-opm-rst-file=1",
                ],
                cwd=output_directory,
                check=True,
            )
            dry_run_deck.unlink(missing_ok=True)
            copy2(source_deck, dry_run_deck)
            print(f"\nCloning {source_deck} to {dry_run_deck.name} \n")
        else:
            copy2(source_deck, dry_run_deck)
            print(
                f"\nCloning {source_deck} to {dry_run_deck.name} for the initial "
                "dry run to generate the grid (.EGRID) and static (.INIT) properties\n"
            )
            subprocess.run(
                [dck.flow_command, dry_run_deck.name, *flags_dry_run.split()],
                cwd=output_directory,
                check=True,
            )
        for output_type in output_types:
            output_file = output_directory / f"{dry_run_name}{output_type}"
            if not output_file.is_file():
                if output_type == ".INIT":
                    print(
                        f"\nThe {output_file} is not found, try adding the keyword INIT "
                        f"in the GRID section in the original deck {dck.input_deck_name}.DATA\n"
                    )
                elif output_type == ".EGRID":
                    print(
                        f"\nThe {output_file} is not found, try removing the keyword "
                        f"GRIDFILE in the GRID section in the original deck {dck.input_deck_name}"
                        ".DATA\n"
                    )
                else:
                    print(
                        f"\nThe {output_file} is not found, check the input deck "
                        f"{dck.input_deck_name}.DATA\n"
                    )
                sys.exit()
        print(
            f"\nThe initial/dry run of {dck.input_deck_name}.DATA succeeded "
            f"(see {output_directory}/)"
        )
    if dck.execution_mode in ("prep_deck", "deck", "deck_dry", "all"):
        dck.original_deck_name = dck.input_deck_name
        dck.input_deck_name = str(output_directory / dry_run_name)
        for output_type in output_types:
            output_file = Path(f"{dck.input_deck_name}{output_type}")
            if not output_file.is_file():
                print(
                    f"\nThe {output_file} is not found, try running pycopm with "
                    "-m prep_deck and without -ijk"
                )
                sys.exit()
        dck.props_keywords = ["permx", "permy", "permz", "poro"]
        dck.base_keywords = dck.props_keywords + ["grid"]
        if dck.refinement_enabled:
            print("\nInitializing pycopm to generate the refined files, please wait.")
        elif dck.vicinity_specification:
            print("\nInitializing pycopm to generate the submodel files, please wait.")
        elif dck.grid_transformation:
            print(
                "\nInitializing pycopm to generate the transformed files, please wait."
            )
        else:
            print("\nInitializing pycopm to generate the coarsened files, please wait.")
        _initialize_deck_data(dck)
        dck.original_cell_count = dck.original_nx * dck.original_ny * dck.original_nz
        if dck.transmissibility_coarsening_method > 0:
            dck.props_keywords.extend(("tranx", "trany", "tranz"))
        dck.original_active_cell_mask = dck.original_porv > 0
        vicinity: VicinityMaps = cast(VicinityMaps, None)
        refinement: RefinementMaps = cast(RefinementMaps, None)
        coarsening: CoarseningMaps = cast(CoarseningMaps, None)
        if dck.refinement_enabled:
            refinement = create_refinement_maps(dck, cmdargs)
        elif dck.vicinity_specification:
            vicinity = create_vicinity_maps(dck)
        elif dck.coarsening_enabled:
            coarsening = create_coarsening_maps(dck, cmdargs)
        if not dck.grid_transformation:
            _create_index_mappings(dck, vicinity, refinement, coarsening)
        if dck.requested_ijk[0]:
            print(
                dck.original_to_output_i[dck.requested_ijk[0][0]],
                dck.original_to_output_j[dck.requested_ijk[0][1]],
                dck.original_to_output_k[dck.requested_ijk[0][2]],
            )
            sys.exit()
        modified_deck, wellcind = process_deck(dck, vicinity)
        print("Processing the mappings")
        cr, zc = np.array([]), np.array([])
        if dck.grid_transformation:
            transform_properties(dck, modified_deck)
            transform_grid(dck)
        elif dck.refinement_enabled:
            refine_properties(dck, refinement, modified_deck)
            refine_grid(dck, refinement)
        elif dck.vicinity_specification:
            map_vicinity_properties(dck, vicinity, modified_deck)
            extract_vicinity_grid(dck, vicinity)
            apply_boundary_pore_volume_correction(dck, vicinity)
            write_porv(dck, modified_deck)
        else:
            cluster_minimum, cluster_maximum, removed_cells = coarsen_properties(
                dck,
                coarsening,
                modified_deck,
                wellcind,
            )
            if dck.pore_volume_correction == 1:
                redistribute_removed_pore_volume(
                    dck,
                    coarsening.cell_groups,
                    cluster_minimum,
                    cluster_maximum,
                    removed_cells,
                )
            write_porv(dck, modified_deck)
            cr, zc = coarsen_corner_point_grid(dck, coarsening)
        generated_deck = output_directory / f"{dck.output_deck_name}.DATA"
        generated_deck.write_text(
            "".join(f"{deck_line}\n" for deck_line in modified_deck),
            encoding="utf8",
        )
        if dck.correct_fluid_in_place == 1:
            _correct_fluid_in_place(dck, modified_deck)
        if (
            dck.coarsening_enabled
            and dck.egrid_file.count("NNC1")
            and dck.transmissibility_coarsening_method > 0
        ):
            print("\nCall OPM Flow for a dry run of the generated model.\n")
            print("\nThis is needed for the nnctrans, please wait.\n")
            subprocess.run(
                [dck.flow_command, generated_deck.name, *flags_dry_run.split()],
                cwd=output_directory,
                check=False,
            )
            generated_grid = output_directory / f"{dck.output_deck_name}.EGRID"
            if (
                OpmFile(str(generated_grid)).count("NNC1")
                or OpmFile(f"{dck.input_deck_name}.EGRID").count("NNC1")
            ) and dck.transmissibility_coarsening_method > 0:
                map_nnc_transmissibilities(dck, coarsening)
            else:
                print("\nNo nnctrans found.")
        if dck.coarsening_enabled:
            if dck.dual_porosity_criterion:
                cr, zc = build_dual_porosity_grid(dck, coarsening, cr, zc)
                write_grid(dck, cr, zc, True)
                write_dual_properties(
                    dck,
                    coarsening,
                    dck.output_nx * (2 * dck.output_ny + 1) * dck.output_nz,
                    modified_deck,
                )
                grid_include_index = modified_deck.index(
                    f"'{dck.include_prefix}GRID.INC' /\n"
                )
                modified_deck.insert(
                    grid_include_index + 1,
                    f"INCLUDE\n'{dck.include_prefix}NNC.INC' /\n",
                )
                dimension_index = modified_deck.index(
                    f"{dck.output_nx} {dck.output_ny} {dck.output_nz} /"
                )
                dual_ny = 2 * dck.output_ny + 1
                modified_deck[dimension_index] = (
                    f"{dck.output_nx} {dual_ny} {dck.output_nz} /"
                )
                generated_deck.write_text(
                    "".join(f"{deck_line}\n" for deck_line in modified_deck),
                    encoding="utf8",
                )
                coarsening.nnc_text += "/\n"
                write_include(
                    output_directory / f"{dck.include_prefix}NNC.INC",
                    "".join(coarsening.nnc_text),
                )
            elif coarsening.nnc_text != "NNC\n":
                grid_include_index = modified_deck.index(
                    f"'{dck.include_prefix}GRID.INC' /\n"
                )
                modified_deck.insert(
                    grid_include_index + 1,
                    f"INCLUDE\n'{dck.include_prefix}NNC.INC' /\n",
                )
                generated_deck.write_text(
                    "".join(f"{deck_line}\n" for deck_line in modified_deck),
                    encoding="utf8",
                )
                coarsening.nnc_text += "/\n"
                write_include(
                    output_directory / f"{dck.include_prefix}NNC.INC",
                    "".join(coarsening.nnc_text),
                )
        print(
            f"\nThe generation of files succeeded, see {generated_deck} and "
            f"{output_directory}/{dck.include_prefix}*.INC\n"
        )
    if dck.execution_mode in ("deck_dry", "dry", "all"):
        print("\nCall OPM Flow for a dry run of the generated model.\n")
        completed_process = subprocess.run(
            [dck.flow_command, f"{dck.output_deck_name}.DATA", *flags_dry_run.split()],
            cwd=output_directory,
            check=False,
        )
        if completed_process.returncode != 0:
            print(
                "\nThe dry run of the generated model "
                f"{output_directory}/{dck.output_deck_name}.DATA failed. Check the Flow "
                "output in the terminal for the error, which might be possible to "
                f"fix by correcting the input deck {source_deck} or the generated "
                "deck; otherwise, please raise an issue at "
                "https://github.com/cssr-tools/pycopm/issues"
            )
        else:
            print(f"\nThe dryrun results have been written to {output_directory}/")


def _correct_fluid_in_place(dck: ConfigViaDeck, modified_deck: list[str]) -> None:
    """Adjust output pore volume to match input oil and gas in place.

    Short Flow runs provide the fluid-in-place values used for two successive pore
    volume corrections.

    Parameters
    ----------
    dck
        Deck configuration whose ``output_porv`` is updated.
    modified_deck
        Generated deck lines used to create the correction case."""
    output_directory = Path(dck.output_directory)
    flags_one_step = (
        "--parsing-strictness=low --check-satfunc-consistency=false "
        "--output-mode=none --solver-max-restarts=20 "
        "--solver-continue-on-convergence-failure=true "
        f"--output-dir={output_directory}"
    )
    threshold = 1e-1
    deck_file = Path(f"{dck.input_deck_name}.DATA")
    deck_lines = deck_file.read_text(encoding="utf8").splitlines()
    schedule_index = deck_lines.index("SCHEDULE")
    deck_lines = deck_lines[: schedule_index + 1] + [
        "TSTEP",
        "0.01 /",
    ]
    restart_index = deck_lines.index("RPTRST")
    restart_options = deck_lines[restart_index + 1].split("/")[0]
    deck_lines[restart_index + 1] = f"{restart_options} FIP /"
    one_step_deck = output_directory / f"{dck.output_deck_name}_1STEP.DATA"
    correction_deck = output_directory / f"{dck.output_deck_name}_CORR.DATA"
    one_step_deck.write_text(
        "".join(f"{deck_line}\n" for deck_line in deck_lines),
        encoding="utf8",
    )
    schedule_index = modified_deck.index("SCHEDULE")
    deckcorr = modified_deck[: schedule_index + 1] + [
        "TSTEP",
        "0.01 /",
    ]
    restart_index = deckcorr.index("RPTRST")
    restart_options = deckcorr[restart_index + 1].split("/")[0]
    deckcorr[restart_index + 1] = f"{restart_options} FIP /"
    correction_deck.write_text(
        "".join(f"{deck_line}\n" for deck_line in deckcorr),
        encoding="utf8",
    )
    print(
        f"\nRunning {one_step_deck} and {correction_deck} to correct the "
        "pore volume\n"
    )
    subprocess.run(
        [dck.flow_command, str(correction_deck), *flags_one_step.split()],
        check=False,
    )
    subprocess.run(
        [dck.flow_command, str(one_step_deck), *flags_one_step.split()],
        check=False,
    )
    reference_restart = OpmFile(
        str(output_directory / f"{dck.output_deck_name}_1STEP.UNRST")
    )
    corrected_restart = OpmFile(
        str(output_directory / f"{dck.output_deck_name}_CORR.UNRST")
    )
    corrected_init = OpmFile(
        str(output_directory / f"{dck.output_deck_name}_CORR.INIT")
    )
    reference_fip_gas = np.asarray(reference_restart["FIPGAS", 0])
    reference_fip_oil = np.asarray(reference_restart["FIPOIL", 0])
    corrected_porv = np.asarray(corrected_init["PORV"])
    corrected_fip_gas = np.asarray(corrected_restart["FIPGAS", 0])
    corrected_fip_oil = np.asarray(corrected_restart["FIPOIL", 0])
    active_porv = corrected_porv[corrected_porv > 0]
    correction_factor = np.sum(reference_fip_oil) / np.sum(corrected_fip_oil) - 1
    low_oil_cells = corrected_fip_oil <= threshold
    high_oil_cells = corrected_fip_oil > threshold
    active_porv[low_oil_cells] -= (
        correction_factor
        * np.sum(active_porv[high_oil_cells])
        / np.count_nonzero(low_oil_cells)
    )
    active_porv[high_oil_cells] *= 1 + correction_factor
    corrected_porv[corrected_porv > 0] = active_porv
    corrected_porv[np.isnan(corrected_porv)] = 0
    dck.output_porv = corrected_porv
    write_porv(dck, modified_deck)
    subprocess.run(
        [dck.flow_command, str(correction_deck), *flags_one_step.split()],
        check=False,
    )
    corrected_restart = OpmFile(
        str(output_directory / f"{dck.output_deck_name}_CORR.UNRST")
    )
    corrected_init = OpmFile(
        str(output_directory / f"{dck.output_deck_name}_CORR.INIT")
    )
    corrected_porv = np.asarray(corrected_init["PORV"])
    corrected_fip_gas = np.asarray(corrected_restart["FIPGAS", 0])
    corrected_fip_oil = np.asarray(corrected_restart["FIPOIL", 0])
    corrected_sgas = np.asarray(corrected_restart["SGAS", 0])
    active_porv = corrected_porv[corrected_porv > 0]
    high_gas_cells = corrected_sgas > threshold
    low_oil_cells = corrected_fip_oil <= threshold
    correction_factor = (
        np.sum(reference_fip_gas) - np.sum(corrected_fip_gas)
    ) / np.sum(corrected_fip_gas[high_gas_cells])
    active_porv[low_oil_cells] -= (
        correction_factor
        * np.sum(active_porv[high_gas_cells])
        / np.count_nonzero(low_oil_cells)
    )
    active_porv[high_gas_cells] *= 1 + correction_factor
    corrected_porv[corrected_porv > 0] = active_porv
    corrected_porv[np.isnan(corrected_porv)] = 0
    dck.output_porv = corrected_porv
    write_porv(dck, modified_deck)
    print(f"\nRunning {correction_deck} with the corrected pore volume\n")
    subprocess.run(
        [dck.flow_command, str(correction_deck), *flags_one_step.split()],
        check=False,
    )


def _create_index_mappings(
    dck: ConfigViaDeck,
    vicinity: VicinityMaps,
    refinement: RefinementMaps,
    coarsening: CoarseningMaps,
) -> None:
    """Create original-to-output mappings for each grid axis.

    Depending on the selected workflow, the mappings represent coarse cells,
    submodel indices, or the first and last cells created by refinement.

    Parameters
    ----------
    dck
        Deck configuration updated with the index mappings.
    vicinity
        Vicinity bounds for submodel extraction.
    refinement
        Per-axis refinement values.
    coarsening
        Per-axis coarsening values."""
    if dck.refinement_enabled:
        for index_name, direction, ref_dir in (
            ("i", "x", refinement.x),
            ("j", "y", refinement.y),
            ("k", "z", refinement.z),
        ):
            original_size = getattr(dck, f"original_n{direction}")
            setattr(
                dck,
                f"original_to_output_{index_name}",
                np.zeros(original_size + 1, dtype=int),
            )
            setattr(
                dck,
                f"original_to_first_refined_{index_name}",
                np.zeros(original_size + 1, dtype=int),
            )
            setattr(
                dck,
                f"original_to_last_refined_{index_name}",
                np.zeros(original_size + 1, dtype=int),
            )
            next_index = 2
            for original_index in range(
                getattr(dck, f"original_to_output_{index_name}").size - 1
            ):
                midpoint_count = 1
                refinement_factor = int(ref_dir[original_index])
                for refinement_index in range(refinement_factor):
                    next_index += 1
                    if refinement_index % 2 == 0:
                        midpoint_count += 1
                getattr(dck, f"original_to_output_{index_name}")[original_index + 1] = (
                    next_index - midpoint_count
                )
                getattr(dck, f"original_to_first_refined_{index_name}")[
                    original_index + 1
                ] = (
                    next_index - 2 * (midpoint_count - 1) - (refinement_factor + 1) % 2
                )
                value = next_index - 1
                getattr(dck, f"original_to_last_refined_{index_name}")[
                    original_index + 1
                ] = value
                next_index += 1
    elif dck.vicinity_specification:
        for index_name, dimension_name, minimum_index, maximum_index in (
            ("i", "x", vicinity.min_i, vicinity.max_i),
            ("j", "y", vicinity.min_j, vicinity.max_j),
            ("k", "z", vicinity.min_k, vicinity.max_k),
        ):
            original_size = getattr(dck, f"original_n{dimension_name}")
            setattr(
                dck,
                f"original_to_output_{index_name}",
                np.zeros(original_size + 1, dtype=int),
            )
            mapped_index = 1
            original_size = getattr(dck, f"original_to_output_{index_name}").size - 1
            for original_index in range(original_size):
                if minimum_index <= original_index + 1 <= maximum_index:
                    getattr(dck, f"original_to_output_{index_name}")[
                        original_index + 1
                    ] = mapped_index
                    mapped_index += 1
            setattr(dck, f"output_n{dimension_name}", mapped_index - 1)
    else:
        for index_name, direction, coa_dir in (
            ("i", "x", coarsening.x),
            ("j", "y", coarsening.y),
            ("k", "z", coarsening.z),
        ):
            original_size = getattr(dck, f"original_n{direction}")
            setattr(
                dck,
                f"original_to_output_{index_name}",
                np.zeros(original_size + 1, dtype=int),
            )
            mapped_index = 1
            for original_index in range(getattr(dck, f"original_n{direction}")):
                source_index = original_index + 1
                if getattr(dck, f"original_to_output_{index_name}")[source_index] == 0:
                    getattr(dck, f"original_to_output_{index_name}")[
                        source_index
                    ] = mapped_index
                    mapped_index += 1
                if coa_dir[source_index] > 1:
                    getattr(dck, f"original_to_output_{index_name}")[
                        source_index + 1
                    ] = getattr(dck, f"original_to_output_{index_name}")[source_index]


def _initialize_deck_data(dck: ConfigViaDeck) -> None:
    """Load dry-run grid and property data into the deck configuration.

    The function opens EGRID, INIT, and optional restart files, determines grid
    dimensions, and collects available property keywords.

    Parameters
    ----------
    dck
        Deck configuration updated with OPM files, dimensions, and keyword lists."""
    special_properties = [
        "swatinit",
        "sowcr",
        "sogcr",
        "swcr",
        "sgu",
        "swl",
        "krwr",
        "krw",
        "krorw",
        "krorg",
        "kro",
        "krgr",
        "krg",
    ]
    dck.egrid_file = OpmFile(f"{dck.input_deck_name}.EGRID")
    dck.grid_model = OpmGrid(f"{dck.input_deck_name}.EGRID")
    dck.init_file = OpmFile(f"{dck.input_deck_name}.INIT")
    for property_name in special_properties:
        if dck.init_file.count(property_name.upper()):
            dck.props_keywords.append(property_name)
            dck.special_keywords.append(property_name)
    multipliers_names = ["multx", "multx-", "multy", "multy-", "multz", "multz-"]
    maindeckmultflt, multipliers_values = find_multiplier_keywords(dck)
    for mlt_val, mlt_name in zip(multipliers_values, multipliers_names):
        keyword = mlt_name.upper()
        if dck.init_file.count(keyword):
            multiplier_deck = np.asarray(dck.init_file[keyword])
            if np.any(multiplier_deck != 1) and (mlt_val or not maindeckmultflt):
                dck.props_keywords.append(mlt_name)
                dck.multipliers_keywords.append(mlt_name)
    for property_name in ("multnum", "fluxnum"):
        keyword = property_name.upper()
        if dck.init_file.count(keyword):
            property_values = np.asarray(dck.init_file[keyword])
            if np.any(property_values != 1):
                dck.grids_keywords.append(property_name)
    for property_name in ("thconr", "disperc"):
        if dck.init_file.count(property_name.upper()):
            dck.grids_keywords.append(property_name)
    for property_name in (
        "endnum",
        "eqlnum",
        "fipnum",
        "imbnum",
        "miscnum",
        "opernum",
        "pvtnum",
        "rocknum",
        "satnum",
    ):
        keyword = property_name.upper()
        if dck.init_file.count(keyword):
            property_values = np.asarray(dck.init_file[keyword])
            if np.any(property_values != 1):
                dck.regions_keywords.append(property_name)
    dck.original_nx, dck.original_ny, dck.original_nz = dck.grid_model.dimension
    dck.output_nx, dck.output_ny, dck.output_nz = dck.grid_model.dimension
    dck.original_porv = np.asarray(dck.init_file["PORV"])
    if dck.write_explicit_solution:
        dck.restart_file = OpmFile(f"{dck.input_deck_name}.UNRST")
        for property_name in (
            "sgas",
            "soil",
            "swat",
            "rs",
            "rv",
            "rsw",
            "rvw",
            "pressure",
            "sbiof",
            "scalc",
            "smicr",
            "soxyg",
            "surea",
            "ssol",
            "spoly",
            "surf",
            "saltp",
            "salt",
        ):
            if dck.restart_file.count(property_name.upper()):
                dck.solution_keywords.append(property_name)
