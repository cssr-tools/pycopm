# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R1702

"""Create configuration objects from command-line arguments and TOML files."""

import argparse
import tomllib
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from opm.io.ecl import EGrid as OpmGrid

from pycopm.config.config import ConfigViaDeck, ConfigViaTOML


def create_deck_config(cmdargs: argparse.Namespace) -> ConfigViaDeck:
    """Create a deck configuration from parsed command arguments.

    Parameters
    ----------
    cmdargs
        Arguments returned by the command-line parser.

    Returns
    -------
    ConfigViaDeck
        Configuration for a deck-based workflow."""
    return ConfigViaDeck(
        output_directory=str(Path(cmdargs.output_directory).expanduser().resolve()),
        flow_command=cmdargs.flow_command,
        input_deck_name=Path(cmdargs.input_deck_path).stem,
        input_deck_path=str(Path(cmdargs.input_deck_path).with_suffix("")),
        active_cell_methods=cmdargs.active_cell_methods.split(","),
        discrete_aggregation_method=cmdargs.discrete_aggregation_method.split(","),
        continuous_aggregation_method=cmdargs.continuous_aggregation_method.split(","),
        jump_thresholds=cmdargs.jump_thresholds.split(","),
        output_deck_name=cmdargs.output_deck_name,
        execution_mode=cmdargs.execution_mode,
        include_prefix=cmdargs.include_prefix,
        requested_ijk=[cmdargs.requested_ijk],
        completion_removal_level=int(cmdargs.completion_removal_level),
        deck_encoding=cmdargs.deck_encoding,
        pore_volume_correction=int(cmdargs.pore_volume_correction),
        correct_fluid_in_place=int(cmdargs.correct_fluid_in_place),
        transmissibility_coarsening_method=int(
            cmdargs.transmissibility_coarsening_method
        ),
        vicinity_specification=cmdargs.vicinity_specification,
        grid_transformation=cmdargs.grid_transformation,
        write_explicit_solution=int(cmdargs.write_explicit_solution) == 1,
        dual_porosity_criterion=cmdargs.dual_porosity_criterion,
        significant_digits=int(cmdargs.significant_digits),
        refinement_enabled=bool(
            cmdargs.x_refinement
            or cmdargs.y_refinement
            or cmdargs.z_refinement
            or cmdargs.refinement
        ),
        coarsening_enabled=bool(
            cmdargs.x_coarsening
            or cmdargs.y_coarsening
            or cmdargs.z_coarsening
            or cmdargs.coarsening
        ),
    )


def parse_axis_modifications(uniform: str, localized: list) -> tuple[NDArray, list]:
    """Parse uniform or axis-specific grid modifications.

    Uniform input contains one value for each axis. Axis-specific input can contain
    explicit arrays; coarsening also accepts one-based indices and inclusive ranges
    such as ``2:4,7``.

    Parameters
    ----------
    uniform
        Comma-separated x, y, and z modification values.
    localized
        Axis-specific specifications in x, y, and z order.

    Returns
    -------
    cijk, axis_values
        Uniform axis values and the three parsed axis-specific arrays. Only one
        representation is populated."""
    if uniform:
        cijk = np.fromstring(uniform, sep=",", dtype=int)
        refs: list = [[], [], []]
    else:
        cijk = np.array([])
        refs = []
        for i in range(3):
            argument = localized[i]
            if argument:
                if ":" in argument:
                    values = [0]
                    index = 1
                    for value in argument.split(","):
                        entry = value.split(":")
                        start_index = int(entry[0])
                        values.extend([0] * max(0, start_index - index))
                        if len(entry) == 2:
                            end_index = int(entry[1])
                            values.extend([2] * max(0, end_index - start_index))
                            index = end_index
                        else:
                            index = start_index
                    values.append(0)
                    refs.append(values)
                else:
                    refs.append(
                        list(np.fromstring(argument, sep=",", dtype=int).tolist())
                    )
            else:
                refs.append([])
    return cijk, refs


def load_toml_config(
    input_file: str,
    output_directory: str,
    resource_directory: str,
    significant_digits: int,
) -> ConfigViaTOML:
    """Load a TOML configuration and derive reference-grid dimensions.

    Parameters
    ----------
    input_file
        TOML configuration path.
    output_directory
        Generated-project directory.
    resource_directory
        Directory containing templates and reference simulations.
    significant_digits
        Precision used when writing floating-point values.

    Returns
    -------
    ConfigViaTOML
        Validated configuration populated with reference-grid metadata."""
    with open(input_file, "rb") as f:
        cfg_file = tomllib.load(f)
    suffixes = cfg_file["cleanup_file_suffixes"]
    cfg_file["cleanup_file_suffixes"] = ",".join(f"'{suffix}'" for suffix in suffixes)
    cfg_file["x_coarsening"] = np.array(cfg_file["x_coarsening"])
    cfg_file["y_coarsening"] = np.array(cfg_file["y_coarsening"])
    cfg_file["z_coarsening"] = np.array(cfg_file["z_coarsening"])
    name = "NORNE_ATW2013" if cfg_file["model_name"] == "norne" else "DROGON"
    case_path = (
        Path(resource_directory)
        / "reference_simulation"
        / cfg_file["model_name"]
        / name
    )
    grid = OpmGrid(f"{case_path}.EGRID")
    cfg = ConfigViaTOML(
        output_directory=output_directory,
        resource_directory=resource_directory,
        significant_digits=significant_digits,
        reference_case_name=name,
        original_nx=grid.dimension[0],
        original_ny=grid.dimension[1],
        original_nz=grid.dimension[2],
        original_cell_count=int(np.prod(grid.dimension)),
        **cfg_file,
    )
    return cfg
