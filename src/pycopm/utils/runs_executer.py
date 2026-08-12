# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0914

"""Run TOML-based simulation studies and generate postprocessing plots."""

import shlex
import stat
import subprocess
import sys
from pathlib import Path

from mako.template import Template

from pycopm.config.config import ConfigViaTOML


def run_simulations(cfg: ConfigViaTOML) -> None:
    """Run the configured OPM Flow or ERT workflow.

    Job scripts are copied to the output project and made executable before a
    single realization or ERT study is started.

    Parameters
    ----------
    cfg
        TOML configuration containing execution mode and commands."""
    project_path = Path(cfg.output_directory)
    source_jobs = Path(cfg.resource_directory) / "jobs"
    target_jobs = project_path / "jobs"
    target_jobs.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["cp", "-a", f"{source_jobs}/.", f"{target_jobs}/."],
        check=True,
    )
    for filename in (
        "PERMX_eval",
        "PERMY_eval",
        "PERMZ_eval",
        "table_eval",
        "time_eval",
        "flow_eval",
    ):
        script_path = target_jobs / f"{filename}.py"
        if script_path.exists():
            script_path.chmod(script_path.stat().st_mode | stat.S_IXUSR)
    if cfg.execution_mode == "single-run":
        subprocess.run(
            ["ert", "test_run", "ert.ert"],
            cwd=project_path,
            check=True,
        )
        simulation_path = (
            project_path / "output" / "simulations" / "realisation-0" / "iter-0"
        )
        subprocess.run(
            [
                *shlex.split(str(cfg.flow_command)),
                str(simulation_path / f"{cfg.reference_case_name}_COARSER.DATA"),
                f"--output-dir={simulation_path}",
            ],
            cwd=project_path,
            check=True,
        )
    elif cfg.execution_mode == "ert":
        subprocess.run(
            ["ert", *shlex.split(str(cfg.ert_arguments)), "ert.ert"],
            cwd=project_path,
            check=True,
        )
    print(f"\nThe simulation results have been written to {project_path}")


def generate_postprocessing_plots(
    cfg: ConfigViaTOML, elapsed_seconds: float, number_tables: int
) -> None:
    """Render and execute the postprocessing script.

    Parameters
    ----------
    cfg
        TOML configuration and plotting settings. ``let_parameters`` is sorted in
        place before rendering.
    elapsed_seconds
        Elapsed preprocessing and simulation time.
    number_tables
        Number of generated saturation-function tables."""
    project_path = Path(cfg.output_directory)
    simulations_path = project_path / "output" / "simulations"
    ensemble_size = len(next(simulations_path.walk())[1])
    number_iterations = 1
    for realisation_index in range(ensemble_size):
        realisation_path = simulations_path / f"realisation-{realisation_index}"
        number_iterations = max(
            number_iterations, len(next(realisation_path.walk())[1])
        )
    cfg.let_parameters = sorted(cfg.let_parameters, key=lambda item: item[0])
    template = Template(
        filename=str(
            Path(cfg.resource_directory)
            / "template_scripts"
            / "common"
            / "plot_post.mako"
        )
    )
    rendered_template = template.render(
        output_directory=cfg.output_directory,
        resource_directory=cfg.resource_directory,
        let_parameters=cfg.let_parameters,
        history_matching_end_date=cfg.history_matching_end_date,
        reference_case_name=cfg.reference_case_name,
        model_name=cfg.model_name,
        observation_relative_errors=cfg.observation_relative_errors,
        observation_minimum_errors=cfg.observation_minimum_errors,
        cleanup_file_suffixes=cfg.cleanup_file_suffixes,
        number_tables=number_tables,
        elapsed_seconds=elapsed_seconds,
        number_iterations=number_iterations,
        ensemble_size=ensemble_size,
    )
    plotting_path = project_path / "jobs" / "plotting.py"
    plotting_path.write_text(rendered_template, encoding="utf8")
    print("\nRunning the postprocessing methods, please wait.")
    subprocess.run(
        [sys.executable, str(plotting_path)],
        cwd=project_path,
        check=True,
    )
