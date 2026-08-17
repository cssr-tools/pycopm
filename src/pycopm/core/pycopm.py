# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0914,R0915

"""Command-line entry point and top-level workflow coordination for pycopm.

pycopm supports two input workflows:

* OPM ``.DATA`` decks can be coarsened, refined, transformed, or reduced to a
  submodel.
* TOML configurations generate coarsened Norne or Drogon cases and can
  optionally run OPM Flow or ERT studies.

This module parses and validates command-line arguments, selects the appropriate
workflow, and coordinates its major processing steps. The numerical and
file-generation details are implemented in the utility modules.
"""

import argparse
import re
import shlex
import shutil
import subprocess
import time
from pathlib import Path

from pycopm.utils.coarsening import coarsen_and_write_properties, create_coarsening_map
from pycopm.utils.files_writer import write_coarsened_model_files
from pycopm.utils.generate_decks import create_deck
from pycopm.utils.input_values import create_deck_config, load_toml_config
from pycopm.utils.runs_executer import generate_postprocessing_plots, run_simulations


def main(argv: list[str] | None = None) -> None:
    """Run the deck-based or TOML-based pycopm workflow.

    OPM ``.DATA`` decks can be coarsened, refined, transformed, or reduced to
    a submodel. TOML configurations generate coarsened Norne or Drogon cases
    and can optionally run OPM Flow or ERT studies.

    Parameters
    ----------
    argv
        Command-line arguments. If omitted, arguments are read from
        ``sys.argv``.

    Other Parameters
    ----------------
    -i, --input_deck_path
        Input ``.DATA`` deck or TOML configuration file.
    -o, --output_directory
        Directory for generated decks, include files, and simulation results.
    -f, --flow_command
        Command or path used to run OPM Flow.
    -m, --execution_mode
        Deck-processing stages to run: ``prep``, ``deck``, ``dry``,
        ``prep_deck``, ``deck_dry``, or ``all``.
    -v, --vicinity_specification
        Submodel selection based on region values, an xy polygon, or a
        well-centred ``box``, ``diamond``, or ``diamondxy`` neighbourhood.
    -c, --coarsening
        Uniform coarsening factors in the x, y, and z directions.
    -x, --x_coarsening
        Cell-specific coarsening specification along the x axis.
    -y, --y_coarsening
        Cell-specific coarsening specification along the y axis.
    -z, --z_coarsening
        Cell-specific coarsening specification along the z axis.
    -g, --refinement
        Uniform numbers of additional cells along the x, y, and z axes.
    -rx, --x_refinement
        Number of additional cells for each original x interval.
    -ry, --y_refinement
        Number of additional cells for each original y interval.
    -rz, --z_refinement
        Number of additional cells for each original z interval.
    -a, --active_cell_methods
        Aggregation method for active-cell values: ``min``, ``max``, or
        ``mode``.
    -n, --discrete_aggregation_method
        Aggregation method for discrete properties: ``min``, ``max``, or
        ``mode``.
    -s, --continuous_aggregation_method
        Aggregation method for continuous properties: ``min``, ``max``,
        ``mean``, or pore-volume-weighted mean (``pvmean``). If omitted,
        property-specific physical aggregation is used.
    -p, --pore_volume_correction
        Pore-volume correction method. The available values are ``0`` through
        ``4``; supported methods depend on the selected workflow.
    -q, --correct_fluid_in_place
        Set to ``1`` to adjust pore volume to match the initial oil and gas in
        place of the input model.
    -t, --transmissibility_coarsening_method
        Transmissibility coarsening method: ``0``, ``1``, or ``2``.
    -r, --completion_removal_level
        Level of COMPDAT data removed after coarsening: ``0``, ``1``, or
        ``2``.
    -j, --jump_thresholds
        Positive depth-jump thresholds used to prevent unwanted connections
        between cells grouped during coarsening.
    -w, --output_deck_name
        Name of the generated OPM deck.
    -l, --include_prefix
        Prefix added to generated include filenames.
    -e, --deck_encoding
        Character encoding used to read the input deck: ``ISO-8859-1`` or
        ``utf8``.
    -ijk, --requested_ijk
        One-based input-grid ``i,j,k`` indices to map to the modified grid.
    -d, --grid_transformation
        Coordinate transformation: ``translate [x,y,z]``, ``scale [x,y,z]``,
        or ``rotatexy``, ``rotatexz``, or ``rotateyz`` followed by an angle
        in degrees.
    -explicit, --write_explicit_solution
        Set to ``1`` to write initial solution properties explicitly instead
        of retaining EQUIL initialization.
    -dual, --dual_porosity_criterion
        Static-property criterion used to separate matrix and fracture or
        non-net cells during coarsening.
    -precision, --significant_digits
        Number of significant digits used when writing floating-point values.
        Set to ``0`` to preserve machine precision.
    """
    start_time = time.monotonic()
    cmdargs = _parse_arguments(argv)
    _check_cmdargs(cmdargs)
    output_folder = Path(cmdargs.output_directory).expanduser().resolve()
    input_file = cmdargs.input_deck_path
    output_folder.mkdir(parents=True, exist_ok=True)

    # Process a DATA deck by coarsening, refining, extracting, or transforming it
    if input_file.endswith(".DATA"):
        dck = create_deck_config(cmdargs)
        create_deck(dck, cmdargs)
        return

    # Process a TOML file by generating a coarsened Norne or Drogon project

    # Load the TOML configuration and derive the reference-model settings
    resource_directory = str(Path(__file__).resolve().parent.parent)
    cfg = load_toml_config(
        input_file,
        str(output_folder),
        resource_directory,
        int(cmdargs.significant_digits),
    )
    cfg.flow_command = _check_flow(cmdargs.flow_command, cfg.flow_command, input_file)
    print(f"\npycopm is generating the input files for {cfg.model_name}, please wait.")

    for folder in ["preprocessing", "parameters", "jobs", "observations"]:
        (output_folder / folder).mkdir(parents=True, exist_ok=True)

    # Build the coarse grid and map fine cells to coarse cells
    coarsening_map = create_coarsening_map(cfg)

    # Aggregate and write the properties for the coarse grid
    number_tables = coarsen_and_write_properties(cfg, coarsening_map)

    # Render the Flow, ERT, observation, parameter, and job files
    write_coarsened_model_files(cfg, number_tables)

    # Copy the model-specific INCLUDE files required by the generated deck
    include_folder = "include" if cfg.model_name == "drogon" else "INCLUDE"
    source_include = (
        Path(cfg.resource_directory)
        / "reference_simulation"
        / cfg.model_name
        / include_folder
    )
    destination_include = output_folder / "preprocessing" / include_folder
    shutil.copytree(source_include, destination_include, dirs_exist_ok=True)
    print(f"\nThe generated files have been written to {cfg.output_directory}")
    if cfg.execution_mode in ["single-run", "ert"]:
        print("\nRunning the simulations, please wait.")
        # Run OPM Flow or the selected ERT workflow
        run_simulations(cfg)

        # Generate the postprocessing plots after the simulations
        generate_postprocessing_plots(cfg, time.monotonic() - start_time, number_tables)


def _parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse supported command-line arguments.

    Unknown arguments are left unprocessed for compatibility with external
    launchers.

    Parameters
    ----------
    argv
        Command-line arguments. If omitted, arguments are read from ``sys.argv``.

    Returns
    -------
    dict[str, str]
        Arguments keyed by their destination names."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Tailor a geological model and optionally run simulations "
        "using OPM Flow. All options can be used with DATA decks, while only "
        "-i, -o, -f, and -precision apply to TOML configuration files. See the "
        "online documentation for examples and detailed option descriptions: "
        "https://cssr-tools.github.io/pycopm/introduction.html#overview",
    )
    parser.add_argument(
        "-i",
        "--input_deck_path",
        type=str.strip,
        default="input.toml",
        help="The base name of the toml configuration file or the name of the deck",
    )
    parser.add_argument(
        "-o",
        "--output_directory",
        type=str.strip,
        default=".",
        help="The base name of the output folder",
    )
    parser.add_argument(
        "-f",
        "--flow_command",
        type=str.strip,
        default="flow",
        help="Set path to flow executable",
    )
    parser.add_argument(
        "-m",
        "--execution_mode",
        type=str.strip,
        choices=["prep", "deck", "dry", "prep_deck", "deck_dry", "all"],
        default="prep_deck",
        help="Parts of pycopm to run",
    )
    parser.add_argument(
        "-v",
        "--vicinity_specification",
        type=str.strip,
        default="",
        help="The location to extract the sub model which can be assigned by "
        "region values (e.g., 'fipnum 2,4'), by a polygon given the xy locations "
        "in meters (e.g., 'xypolygon [0,0] [30,0] [30,30] [0,0]'), or by the name "
        "of the well and three different options for the neighbourhood: box, "
        "diamond, and diamondxy (e.g., 'welln box [-1,1] [-2,2] [0,3]')",
    )
    parser.add_argument(
        "-c",
        "--coarsening",
        type=str.strip,
        default="",
        help="Level of coarsening in the x, y, and z dir",
    )
    parser.add_argument(
        "-x",
        "--x_coarsening",
        type=str.strip,
        default="",
        help="Array of x coarsening",
    )
    parser.add_argument(
        "-y",
        "--y_coarsening",
        type=str.strip,
        default="",
        help="Array of y coarsening",
    )
    parser.add_argument(
        "-z",
        "--z_coarsening",
        type=str.strip,
        default="",
        help="Array of z coarsening",
    )
    parser.add_argument(
        "-g",
        "--refinement",
        type=str.strip,
        default="",
        help="Level of grid refinement in the x, y, and z dir",
    )
    parser.add_argument(
        "-rx",
        "--x_refinement",
        type=str.strip,
        default="",
        help="Array of x refinement",
    )
    parser.add_argument(
        "-ry",
        "--y_refinement",
        type=str.strip,
        default="",
        help="Array of y refinement",
    )
    parser.add_argument(
        "-rz",
        "--z_refinement",
        type=str.strip,
        default="",
        help="Array of z refinement",
    )
    parser.add_argument(
        "-a",
        "--active_cell_methods",
        type=str.strip,
        default="mode",
        help="Select aggregation method (min, max, or mode) for the active "
        "cells (for coarsening in the z direction separate by commas to "
        "specify an approach per layer)",
    )
    parser.add_argument(
        "-n",
        "--discrete_aggregation_method",
        type=str.strip,
        default="mode",
        help="Select aggregation method for the discrete variables (min, max, mode)",
    )
    parser.add_argument(
        "-s",
        "--continuous_aggregation_method",
        type=str.strip,
        default="",
        help="Select aggregation method for the continuous variables (min, max, mean, "
        "pvmean; by default these are property/direction dependent, e.g., harmonic "
        "average for permeability",
    )
    parser.add_argument(
        "-p",
        "--pore_volume_correction",
        type=str.strip,
        choices=["0", "1", "2", "3", "4"],
        default="0",
        help="Select pore volume correction approach",
    )
    parser.add_argument(
        "-q",
        "--correct_fluid_in_place",
        type=str.strip,
        choices=["0", "1"],
        default="0",
        help="Adjust the pv to the initial FGIP and FOIP",
    )
    parser.add_argument(
        "-t",
        "--transmissibility_coarsening_method",
        type=str.strip,
        choices=["0", "1", "2"],
        default="0",
        help="Select coarsening method for transmissibilities",
    )
    parser.add_argument(
        "-r",
        "--completion_removal_level",
        type=str.strip,
        choices=["0", "1", "2"],
        default="2",
        help="Select COMPDAT entries to remove after coarsening",
    )
    parser.add_argument(
        "-j",
        "--jump_thresholds",
        type=str.strip,
        default="",
        help="Parameter to avoid creation of neighbouring connections after coarsening",
    )
    parser.add_argument(
        "-w",
        "--output_deck_name",
        type=str.strip,
        default="",
        help="Name of the generated deck",
    )
    parser.add_argument(
        "-l",
        "--include_prefix",
        type=str.strip,
        default="PYCOPM_",
        help="Added text before each generated .INC",
    )
    parser.add_argument(
        "-e",
        "--deck_encoding",
        type=str.strip,
        choices=["ISO-8859-1", "utf8"],
        default="ISO-8859-1",
        help="Encoding to read the deck",
    )
    parser.add_argument(
        "-ijk",
        "--requested_ijk",
        type=str.strip,
        default="",
        help="Returns the modified indices given as entry the 'i,j,k' indices",
    )
    parser.add_argument(
        "-d",
        "--grid_transformation",
        type=str.strip,
        default="",
        help="Select transformation method (e.g, 'translate [10,-5,4]', "
        "'scale [1,2,3]', or 'rotatexy 45')",
    )
    parser.add_argument(
        "-explicit",
        "--write_explicit_solution",
        type=str.strip,
        choices=["0", "1"],
        default="0",
        help="Set to 1 to explicitly write the cell values in the SOLUTION section",
    )
    parser.add_argument(
        "-dual",
        "--dual_porosity_criterion",
        type=str.strip,
        default="",
        help="Set the criterium to differentiate net and non-net in coarsening using a static "
        "variable. To remove the vertical transfer function (FT) between net and not-net cells, "
        "add to the command ', vertical TF = 0', e.g., 'poro <= 0.1' (which includes vertical TF) "
        "or 'poro <= 0.1, vertical TF = 0'",
    )
    parser.add_argument(
        "-precision",
        "--significant_digits",
        type=str.strip,
        choices=[str(value) for value in range(16)],
        default="7",
        help="Set the number of significant digits used when writing floating-point values, or 0 "
        "to use machine precision",
    )
    return parser.parse_args(argv)


def _check_cmdargs(cmdargs: argparse.Namespace) -> None:
    """Validate command-line arguments and incompatible operations.

    The checks cover input type, Flow availability, coarsening and refinement
    syntax, aggregation methods, vicinity selections, transformations, and
    options restricted to particular workflows.

    Parameters
    ----------
    cmdargs
        Parsed arguments returned by :func:`_parse_arguments`.

    Raises
    ------
    SystemExit
        If an argument is invalid or an incompatible combination is requested."""
    input_file = cmdargs.input_deck_path
    # Select the workflow from the input filename extension
    if not input_file.endswith((".DATA", ".toml")):
        print(
            f"\nInvalid extension for input file '-i {input_file}', "
            "valid extensions are .DATA or .toml\n"
        )
        raise SystemExit(1)
    if not cmdargs.output_directory:
        print("\nInvalid value for '-o', the output folder cannot be empty.\n")
        raise SystemExit(1)
    # Only -i, -o, -f, and -precision apply to TOML configuration files
    if input_file.endswith(".toml"):
        data_options = {
            "-m": ("execution_mode", "prep_deck"),
            "-v": ("vicinity_specification", ""),
            "-c": ("coarsening", ""),
            "-x": ("x_coarsening", ""),
            "-y": ("y_coarsening", ""),
            "-z": ("z_coarsening", ""),
            "-g": ("refinement", ""),
            "-rx": ("x_refinement", ""),
            "-ry": ("y_refinement", ""),
            "-rz": ("z_refinement", ""),
            "-a": ("active_cell_methods", "mode"),
            "-n": ("discrete_aggregation_method", "mode"),
            "-s": ("continuous_aggregation_method", ""),
            "-p": ("pore_volume_correction", "0"),
            "-q": ("correct_fluid_in_place", "0"),
            "-t": ("transmissibility_coarsening_method", "0"),
            "-r": ("completion_removal_level", "2"),
            "-j": ("jump_thresholds", ""),
            "-w": ("output_deck_name", ""),
            "-l": ("include_prefix", "PYCOPM_"),
            "-e": ("deck_encoding", "ISO-8859-1"),
            "-ijk": ("requested_ijk", ""),
            "-d": ("grid_transformation", ""),
            "-explicit": ("write_explicit_solution", "0"),
            "-dual": ("dual_porosity_criterion", ""),
        }
        invalid_options = [
            option
            for option, (name, default) in data_options.items()
            if getattr(cmdargs, name) != default
        ]
        if invalid_options:
            print(
                "\nInvalid option for a toml configuration file; only '-i', '-o', "
                "'-f', and '-precision' can be used. Invalid options: "
                f"{', '.join(invalid_options)}.\n"
            )
            raise SystemExit(1)
        return
    # Verify the complete Flow command, including any launcher and arguments
    try:
        flow_arguments = shlex.split(cmdargs.flow_command)
    except ValueError:
        flow_arguments = []
    if not flow_arguments:
        print(f"\nInvalid OPM flow command '-f {cmdargs.flow_command}'.\n")
        raise SystemExit(1)
    try:
        flow_result = subprocess.run(
            [*flow_arguments, "-h"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except OSError:
        flow_result = None
    if flow_result is None or flow_result.returncode != 0:
        print(
            f"\nThe OPM flow executable '-f {cmdargs.flow_command}' "
            "is not available or not working.\n"
        )
        raise SystemExit(1)
    coarsening = cmdargs.coarsening
    x_coarsening = cmdargs.x_coarsening
    y_coarsening = cmdargs.y_coarsening
    z_coarsening = cmdargs.z_coarsening
    refinement = cmdargs.refinement
    x_refinement = cmdargs.x_refinement
    y_refinement = cmdargs.y_refinement
    z_refinement = cmdargs.z_refinement
    vicinity = cmdargs.vicinity_specification
    transformation = cmdargs.grid_transformation
    directional_coarsening = any([x_coarsening, y_coarsening, z_coarsening])
    directional_refinement = any([x_refinement, y_refinement, z_refinement])
    has_coarsening = bool(coarsening or directional_coarsening)
    has_refinement = bool(refinement or directional_refinement)
    # General and directional coarsening options are mutually exclusive
    if coarsening and directional_coarsening:
        print(
            "\nInvalid combination, either set '-c' or the '-x', '-y', and '-z' "
            "flags.\n"
        )
        raise SystemExit(1)
    # General and directional refinement options are mutually exclusive
    if refinement and directional_refinement:
        print(
            "\nInvalid combination, either set '-g' or the '-rx', '-ry', and "
            "'-rz' flags.\n"
        )
        raise SystemExit(1)
    # Coarsening and refinement are mutually exclusive
    if has_coarsening and has_refinement:
        print("\nInvalid combination, either set coarsening or refinement options.\n")
        raise SystemExit(1)
    # Vicinity extraction, transformation, and refinement are mutually exclusive
    if vicinity and transformation:
        print("\nInvalid combination, either set '-v' or '-d'.\n")
        raise SystemExit(1)
    if vicinity and has_refinement:
        print("\nInvalid combination, either set '-v' or refinement options.\n")
        raise SystemExit(1)
    if transformation and has_refinement:
        print("\nInvalid combination, either set '-d' or refinement options.\n")
        raise SystemExit(1)
    # Validate uniform coarsening and refinement levels
    level_pattern = re.compile(r"\d+,\d+,\d+")
    if coarsening and not level_pattern.fullmatch(coarsening):
        print(
            f"\nInvalid value '-c {coarsening}', expected three non-negative "
            "integers separated by commas, e.g., '-c 2,2,1'.\n"
        )
        raise SystemExit(1)
    if refinement and not level_pattern.fullmatch(refinement):
        print(
            f"\nInvalid value '-g {refinement}', expected three non-negative "
            "integers separated by commas, e.g., '-g 2,2,1'.\n"
        )
        raise SystemExit(1)
    # Validate directional coarsening arrays, indices, and ranges
    coarsening_array_pattern = re.compile(r"\d+(?:,\d+)*")
    coarsening_group_pattern = re.compile(
        r"[1-9]\d*(?::[1-9]\d*)?(?:,[1-9]\d*(?::[1-9]\d*)?)*"
    )
    for option, value in [
        ("-x", x_coarsening),
        ("-y", y_coarsening),
        ("-z", z_coarsening),
    ]:
        if value and not (
            coarsening_array_pattern.fullmatch(value)
            or coarsening_group_pattern.fullmatch(value)
        ):
            print(
                f"\nInvalid value '{option} {value}', expected a non-negative "
                "coarsening array or positive indices and ranges separated by "
                "commas.\n"
            )
            raise SystemExit(1)
        if ":" in value:
            for entry in value.split(","):
                if ":" not in entry:
                    continue
                start, end = (int(index) for index in entry.split(":"))
                if start > end:
                    print(
                        f"\nInvalid range '{entry}' in '{option} {value}', "
                        "the end must not be smaller than the start.\n"
                    )
                    raise SystemExit(1)
    # Validate directional refinement arrays
    refinement_array_pattern = re.compile(r"\d+(?:,\d+)*")
    for option, value in [
        ("-rx", x_refinement),
        ("-ry", y_refinement),
        ("-rz", z_refinement),
    ]:
        if value and not refinement_array_pattern.fullmatch(value):
            print(
                f"\nInvalid value '{option} {value}', expected non-negative "
                "integers separated by commas.\n"
            )
            raise SystemExit(1)
    # Validate aggregation methods
    aggregation_options = [
        ("-a", "active_cell_methods", ["min", "max", "mode"]),
        ("-n", "discrete_aggregation_method", ["min", "max", "mode"]),
        (
            "-s",
            "continuous_aggregation_method",
            ["min", "max", "mean", "pvmean"],
        ),
    ]
    z_groups = z_coarsening.split(",") if ":" in z_coarsening else []
    for option, name, valid_methods in aggregation_options:
        value = getattr(cmdargs, name).strip()
        methods = value.split(",") if value else []
        if any(method not in valid_methods for method in methods):
            print(
                f"\nInvalid value '{option} {value}', valid values are "
                f"{', '.join(valid_methods)}.\n"
            )
            raise SystemExit(1)
        if len(methods) > 1 and not z_groups:
            print(
                f"\nInvalid value '{option} {value}', multiple aggregation "
                "methods require range coarsening with '-z'.\n"
            )
            raise SystemExit(1)
        if len(methods) > 1 and len(methods) != len(z_groups):
            print(
                f"\nInvalid value '{option} {value}', expected one aggregation "
                "method for each index or range provided with '-z'.\n"
            )
            raise SystemExit(1)
    # Options controlling property aggregation require coarsening
    if not has_coarsening:
        if cmdargs.active_cell_methods != "mode":
            print("\nInvalid combination, '-a' can only be used with coarsening.\n")
            raise SystemExit(1)
        if cmdargs.discrete_aggregation_method != "mode":
            print("\nInvalid combination, '-n' can only be used with coarsening.\n")
            raise SystemExit(1)
        if cmdargs.continuous_aggregation_method:
            print("\nInvalid combination, '-s' can only be used with coarsening.\n")
            raise SystemExit(1)
        if cmdargs.transmissibility_coarsening_method != "0":
            print("\nInvalid combination, '-t' can only be used with coarsening.\n")
            raise SystemExit(1)
        if cmdargs.jump_thresholds:
            print("\nInvalid combination, '-j' can only be used with coarsening.\n")
            raise SystemExit(1)
        if cmdargs.dual_porosity_criterion:
            print("\nInvalid combination, '-dual' can only be used with coarsening.\n")
            raise SystemExit(1)
    # Fluid-in-place correction is not supported for extracted submodels
    if vicinity and cmdargs.correct_fluid_in_place == "1":
        print("\nInvalid combination, '-q' cannot be used with '-v'.\n")
        raise SystemExit(1)
    # Validate pore-volume correction combinations
    pore_volume_correction = cmdargs.pore_volume_correction
    if pore_volume_correction == "1" and not (has_coarsening or vicinity):
        print("\nInvalid combination, '-p 1' requires coarsening or '-v'.\n")
        raise SystemExit(1)
    if pore_volume_correction in ["2", "3", "4"] and not vicinity:
        print(
            f"\nInvalid combination, '-p {pore_volume_correction}' can only be "
            "used with '-v'.\n"
        )
        raise SystemExit(1)
    # Validate the jump thresholds
    jump_thresholds = cmdargs.jump_thresholds
    if jump_thresholds:
        try:
            jump_values = [float(value.strip()) for value in jump_thresholds.split(",")]
        except ValueError:
            jump_values = []
        if not jump_values or any(value <= 0 for value in jump_values):
            print(
                f"\nInvalid value '-j {jump_thresholds}', expected positive "
                "numbers separated by commas.\n"
            )
            raise SystemExit(1)
    # Validate requested input-model indices
    requested_ijk = cmdargs.requested_ijk
    if requested_ijk and not re.fullmatch(
        r"[1-9]\d*\s*,\s*[1-9]\d*\s*,\s*[1-9]\d*",
        requested_ijk,
    ):
        print(
            f"\nInvalid value '-ijk {requested_ijk}', expected three positive "
            "indices separated by commas, e.g., '-ijk 1,2,3'.\n"
        )
        raise SystemExit(1)
    # Validate coordinate transformations
    number = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    vector_transformation = re.fullmatch(
        rf"(translate|scale)\s+\[\s*{number}\s*,\s*{number}\s*,\s*" rf"{number}\s*\]",
        transformation,
    )
    rotation_transformation = re.fullmatch(
        rf"(rotatexy|rotatexz|rotateyz)\s+{number}",
        transformation,
    )
    if transformation and not (vector_transformation or rotation_transformation):
        print(
            f"\nInvalid value '-d {transformation}', expected "
            "'translate [x,y,z]', 'scale [x,y,z]', or 'rotatexy', 'rotatexz', "
            "or 'rotateyz' followed by an angle.\n"
        )
        raise SystemExit(1)
    if vector_transformation and vector_transformation.group(1) == "scale":
        coordinates = re.findall(number, transformation)
        if any(float(value) == 0 for value in coordinates):
            print(
                f"\nInvalid value '-d {transformation}', scale values cannot be "
                "zero.\n"
            )
            raise SystemExit(1)
    # Validate vicinity extraction specifications
    region_vicinity = re.fullmatch(
        r"[A-Za-z][A-Za-z0-9_]*\s+[1-9]\d*(?:\s*,\s*[1-9]\d*)*",
        vicinity,
    )
    polygon_point = rf"\[\s*{number}\s*,\s*{number}\s*\]"
    polygon_vicinity = re.fullmatch(
        rf"xypolygon(?:\s+{polygon_point}){{4,}}",
        vicinity,
    )
    box_vicinity = re.fullmatch(
        r"\S+\s+box(?:\s+\[\s*-?\d+\s*,\s*-?\d+\s*\]){3}",
        vicinity,
    )
    diamond_vicinity = re.fullmatch(
        r"\S+\s+(?:diamond|diamondxy)\s+\d+",
        vicinity,
    )
    if vicinity and not (
        region_vicinity or polygon_vicinity or box_vicinity or diamond_vicinity
    ):
        print(
            f"\nInvalid value '-v {vicinity}', expected a region selection, an "
            "'xypolygon' specification, or a well followed by 'box', "
            "'diamond', or 'diamondxy'.\n"
        )
        raise SystemExit(1)
    if polygon_vicinity:
        polygon_points = re.findall(polygon_point, vicinity)
        first_point = re.findall(number, polygon_points[0])
        last_point = re.findall(number, polygon_points[-1])
        if first_point != last_point:
            print(
                f"\nInvalid value '-v {vicinity}', the first and last "
                "xypolygon points must be equal.\n"
            )
            raise SystemExit(1)
    if box_vicinity:
        intervals = re.findall(
            r"\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]",
            vicinity,
        )
        if any(int(start) > int(end) for start, end in intervals):
            print(
                f"\nInvalid value '-v {vicinity}', the end of each box interval "
                "must not be smaller than its start.\n"
            )
            raise SystemExit(1)
    # Validate the dual-porosity criterion
    dual_porosity_criterion = cmdargs.dual_porosity_criterion
    dual_criterion_pattern = re.compile(
        rf"[A-Za-z][A-Za-z0-9_]*\s*(?:<=|>=|==|!=|<|>)\s*{number}"
        r"(?:\s*,\s*vertical\s+TF\s*=\s*0)?",
        re.IGNORECASE,
    )
    if dual_porosity_criterion and not dual_criterion_pattern.fullmatch(
        dual_porosity_criterion
    ):
        print(
            f"\nInvalid value '-dual {dual_porosity_criterion}', expected a "
            "static property criterion such as 'poro <= 0.1', optionally "
            "followed by ', vertical TF = 0'.\n"
        )
        raise SystemExit(1)


def _check_flow(flow_cmdargs: str, flow_toml: str, input_file: str) -> str:
    """Select an available OPM Flow command for a TOML workflow.

    Parameters
    ----------
    flow_cmdargs
        Flow command supplied through the command line.
    flow_toml
        Flow command read from the TOML configuration.
    input_file
        TOML filename used in validation messages.

    Returns
    -------
    str
        The selected Flow command.

    Raises
    ------
    SystemExit
        If neither command identifies a working Flow executable."""
    flowpth = str(
        next((value for value in shlex.split(flow_toml) if "flow" in value), False)
    )
    if not flowpth:
        print(
            f"\nflow is not included in the configuration file {input_file}.\n"
            "See the pycopm documentation.\n"
        )
        raise SystemExit(1)

    toml_command = shlex.split(flowpth) + ["-h"]
    flag_command = shlex.split(flow_cmdargs) + ["-h"]

    def flow_exists(command: list[str]) -> bool:
        try:
            return (
                subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.STDOUT,
                    check=False,
                ).returncode
                == 0
            )
        except OSError:
            return False

    toml_ok = flow_exists(toml_command)
    flag_ok = flow_exists(flag_command)

    if not (toml_ok or flag_ok):
        print(
            f"\nThe OPM flow executable '{flowpth}' is not found; "
            "try to install it following the pycopm documentation.\nIf it was "
            "built from source, then either add the folder location to your path, "
            "or write the path\nto flow in the toml configuration file "
            "(e.g., flow = '/home/pycopm/build/opm-simulators/bin/flow'),\n"
            "or using the command flag -f or --flow.\n"
        )
        raise SystemExit(1)
    if toml_ok:
        flow_command = flow_toml
    else:
        command_parts = shlex.split(flow_cmdargs)
        for index, value in enumerate(command_parts):
            if "flow" in value:
                command_parts[index] = flow_cmdargs
                break
        flow_command = " ".join(command_parts)
    return flow_command
