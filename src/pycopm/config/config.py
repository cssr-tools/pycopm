# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=C0103,R0902

"""Configuration models shared across pycopm workflows.

ConfigViaDeck stores command-line options and runtime state for processing a
user-provided OPM deck. ConfigViaTOML stores TOML settings and runtime state for
the predefined Norne and Drogon workflows.

Both objects are mutable because grid dimensions, mappings, properties, and OPM
file handles are populated progressively during processing.
"""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid
from opm.io.ecl import ERst as OpmRestart


@dataclass(slots=True)
class ConfigViaDeck:
    """Options and runtime state for modifying an OPM deck.

    Original-grid values remain unchanged after loading. Output-grid values are
    populated by coarsening, refinement, vicinity extraction, or transformation.
    Grid-index mappings are one-based unless used directly as NumPy indices.

    Attributes
    ----------
    output_directory
        Directory for the generated deck and include files.
    flow_command
        Command used to run OPM Flow.
    input_deck_name, output_deck_name
        Input and generated case names without filename extensions.
    execution_mode
        Processing stages selected with ``--execution_mode``.
    include_prefix
        Prefix added to generated include filenames.
    requested_ijk
        Optional input-grid indices to map to the output grid.
    completion_removal_level
        Level of COMPDAT data removed during deck rewriting.
    deck_encoding
        Character encoding used to read the input deck.
    pore_volume_correction
        Pore-volume correction method selected by ``--pore_volume_correction``.
    correct_fluid_in_place
        Whether output pore volume is adjusted to match initial oil and gas in place.
    transmissibility_coarsening_method
        Method used to aggregate transmissibilities.
    vicinity_specification
        Region, polygon, or well-centred submodel selection.
    grid_transformation
        Translation, scaling, or rotation specification.
    write_explicit_solution
        Whether initial solution properties are written explicitly.
    dual_porosity_criterion
        Static-property criterion separating matrix and fracture cells.
    active_cell_methods, discrete_aggregation_method, continuous_aggregation_method
        Aggregation methods, either global or specified per coarse layer.
    jump_thresholds
        Optional depth-jump thresholds used to deactivate coarse cells.
    significant_digits
        Precision used when writing floating-point values.
    refinement_enabled, coarsening_enabled
        Whether the corresponding grid-modification workflow is active.
    original_nx, original_ny, original_nz
        Original grid dimensions.
    output_nx, output_ny, output_nz
        Generated grid dimensions.
    original_to_output_i, original_to_output_j, original_to_output_k
        One-based mappings from original axis indices to output indices.
    original_to_first_refined_i, original_to_first_refined_j, original_to_first_refined_k
        First output index generated from each original interval.
    original_to_last_refined_i, original_to_last_refined_j, original_to_last_refined_k
        Last output index generated from each original interval.
    original_porv, output_porv, output_actnum
        Original pore volume and generated pore-volume and activity arrays.
    egrid_file, grid_model, init_file, restart_file
        OPM objects opened while processing the input case.
    props_keywords, regions_keywords, grids_keywords, solution_keywords
        Property names discovered in the input model and mapped to the output grid."""

    # User configuration parsed from command-line arguments
    output_directory: str
    flow_command: str
    input_deck_name: str
    output_deck_name: str
    execution_mode: str
    include_prefix: str
    requested_ijk: list
    completion_removal_level: int  # COMPDAT modification level: 0, 1, or 2
    deck_encoding: str
    pore_volume_correction: int  # Correction method selected with the CLI
    correct_fluid_in_place: int  # Whether to match initial FGIP and FOIP
    transmissibility_coarsening_method: int
    vicinity_specification: str
    grid_transformation: str
    write_explicit_solution: bool
    dual_porosity_criterion: str
    active_cell_methods: list[str]  # One method globally or one per layer
    discrete_aggregation_method: list[str]  # One method globally or one per layer
    continuous_aggregation_method: list[str]  # One method globally or one per layer
    jump_thresholds: list[str]  # One threshold globally or one per layer
    significant_digits: int
    refinement_enabled: bool
    coarsening_enabled: bool

    # Input and working deck paths
    input_deck_path: str  # Input path without the .DATA extension
    original_deck_name: str = ""

    # OPM objects loaded from the preprocessing run
    egrid_file: OpmFile = None  # Raw EGRID keyword access
    grid_model: OpmGrid = None  # Grid geometry and index operations
    init_file: OpmFile = None
    restart_file: OpmRestart = None

    # Original- and output-grid dimensions
    original_nx: int = 0
    original_ny: int = 0
    original_nz: int = 0
    output_nx: int = 0
    output_ny: int = 0
    output_nz: int = 0
    original_cell_count: int = 0
    output_cell_count: int = 0

    # Keywords grouped by their OPM deck section or processing behavior
    props_keywords: list = field(default_factory=list)
    base_keywords: list = field(default_factory=list)
    regions_keywords: list = field(default_factory=list)
    grids_keywords: list = field(default_factory=list)
    solution_keywords: list = field(default_factory=list)
    multipliers_keywords: list = field(default_factory=list)
    special_keywords: list = field(default_factory=list)

    # Original-grid arrays in global cell order
    original_porv: NDArray = field(default_factory=lambda: np.array([]))
    original_active_cell_mask: NDArray = field(default_factory=lambda: np.array([]))

    # One-based mappings from original axis indices to output axis indices
    original_to_output_i: NDArray = field(default_factory=lambda: np.array([]))
    original_to_first_refined_i: NDArray = field(default_factory=lambda: np.array([]))
    original_to_last_refined_i: NDArray = field(default_factory=lambda: np.array([]))
    original_to_output_j: NDArray = field(default_factory=lambda: np.array([]))
    original_to_first_refined_j: NDArray = field(default_factory=lambda: np.array([]))
    original_to_last_refined_j: NDArray = field(default_factory=lambda: np.array([]))
    original_to_output_k: NDArray = field(default_factory=lambda: np.array([]))
    original_to_first_refined_k: NDArray = field(default_factory=lambda: np.array([]))
    original_to_last_refined_k: NDArray = field(default_factory=lambda: np.array([]))

    # Output-grid arrays in global cell order
    output_actnum: NDArray = field(default_factory=lambda: np.array([]))
    output_porv: NDArray = field(default_factory=lambda: np.array([]))


@dataclass(slots=True)
class ConfigViaTOML:
    """Settings and runtime state for a TOML-based workflow.

    TOML fields control reference-model coarsening, simulation, and ERT settings.
    Runtime fields are derived after loading the Norne or Drogon reference case.

    Attributes
    ----------
    flow_command
        Command used to run OPM Flow.
    model_name
        Reference model, currently ``norne`` or ``drogon``.
    execution_mode
        Generated-files, single-run, or ERT workflow.
    ensemble_size, max_parallel_realizations
        Ensemble size and maximum concurrent realizations.
    max_realization_runtime_seconds
        Runtime limit per realization; zero disables the limit.
    min_successful_realizations
        Minimum number of successful realizations required by ERT.
    random_seed
        ERT random seed; zero disables deterministic seeding.
    saturation_function_method
        Reference or LET saturation-function method.
    pore_volume_correction
        Whether total pore volume is preserved after coarsening.
    initialization_method
        EQUIL-based or mapped fine-scale initialization.
    observation_relative_errors, observation_minimum_errors
        Relative and minimum uncertainty assigned to observations.
    history_matching_end_date
        Last date included in history matching.
    ert_arguments
        Additional arguments passed to ERT.
    let_parameters
        LET coefficient names, values, and estimation settings.
    rock_property_settings
        Permeability parameterization and aggregation settings.
    x_coarsening, y_coarsening, z_coarsening
        Axis arrays identifying intervals removed during coarsening.
    satnum_generation_method
        Method used to construct SATNUM for the coarse model.
    cleanup_file_suffixes
        File suffixes removed by generated cleanup jobs.
    output_directory, resource_directory
        Generated-project and packaged-resource directories.
    reference_case_name
        Name of the selected reference simulation.
    use_let_tables
        Whether generated LET tables are included in the workflow.
    significant_digits
        Precision used when writing floating-point values.
    original_nx, original_ny, original_nz
        Reference-grid dimensions.
    output_nx, output_ny, output_nz
        Coarsened-grid dimensions.
    original_cell_count
        Number of cells in the reference grid.
    original_to_output_i, original_to_output_j, original_to_output_k
        One-based mappings from fine-grid axes to coarse-grid axes."""

    # Settings read directly from the TOML file
    flow_command: str
    model_name: str  # Supported reference model, such as norne or drogon
    execution_mode: str  # single-run, files, or ert
    ensemble_size: int
    max_parallel_realizations: int
    max_realization_runtime_seconds: int  # Zero means no runtime limit
    min_successful_realizations: int
    random_seed: int  # Zero disables deterministic seeding
    saturation_function_method: int  # Default or LET saturation functions
    pore_volume_correction: int
    initialization_method: int  # EQUIL or fine-scale initialization
    observation_relative_errors: list[float]
    observation_minimum_errors: list[float]
    history_matching_end_date: str
    ert_arguments: str
    let_parameters: list[list]
    rock_property_settings: list[list]
    x_coarsening: NDArray
    y_coarsening: NDArray
    z_coarsening: NDArray
    satnum_generation_method: int = 0
    cleanup_file_suffixes: str = ""

    # Values derived while initializing the selected reference case
    output_directory: str = ""
    resource_directory: str = ""
    reference_case_name: str = ""
    use_let_tables: bool = False
    significant_digits: int = 7

    # Original- and output-grid dimensions
    original_nx: int = 0
    original_ny: int = 0
    original_nz: int = 0
    output_nx: int = 0
    output_ny: int = 0
    output_nz: int = 0
    original_cell_count: int = 0

    # One-based mappings from fine-grid axes to coarse-grid axes
    original_to_output_i: NDArray = field(default_factory=lambda: np.array([]))
    original_to_output_j: NDArray = field(default_factory=lambda: np.array([]))
    original_to_output_k: NDArray = field(default_factory=lambda: np.array([]))
