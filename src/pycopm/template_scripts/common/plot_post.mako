# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
#!/usr/bin/env python3

"""Script to visualize time-series quantities after the history-matching run."""

import csv
import datetime
import shutil
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from opm.io.ecl import EGrid as OpmGrid
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import ESmry as OpmSummary


def visualizeData():
    """Visualize ensemble time series, saturation functions, parameters, and diagnostics."""

    output_folder = Path('${output_directory}')
    pycopm_path = Path('${resource_directory}')
    num_satn = ${number_tables}
    num_para = ${len(let_parameters)}
    name_para = [
    % for i in range(len(let_parameters)):
    '${str(let_parameters[i][0])}'${'\n' if loop.last else ','}\
    % endfor
    ]
    dist_para = [
    % for i in range(len(let_parameters)):
    '${str(let_parameters[i][3])} [${let_parameters[i][4]}, ${let_parameters[i][5]}]'${'\n' if loop.last else ','}\
    % endfor
    ]

    num_realizations = ${ensemble_size}
    num_iterations = ${number_iterations}
    training = datetime.datetime.fromisoformat("${history_matching_end_date}")
    well_types = ["WWPR", "WOPR", "WGPR"]
    field_types = ["FWPT", "FOPT", "FGPT"]
    densities = dict(zip(well_types, [999.04100, 852.95669, 0.90358]))
    field_by_well = dict(zip(well_types, field_types))
    colors = {
        "initial": [51 / 255.0, 153 / 255.0, 255 / 255.0],
        "final": [0 / 255.0, 204 / 255.0, 0 / 255.0],
        "closest": [255 / 255.0, 87 / 255.0, 51 / 255.0],
        "data": [128 / 255.0, 128 / 255.0, 128 / 255.0],
    }
    postprocessing = output_folder / "postprocessing"
    simulations = output_folder / "output" / "simulations"
    shutil.rmtree(postprocessing, ignore_errors=True)
    for folder in ["wells", "parameters", "saturation_functions"]:
        (postprocessing / folder).mkdir(parents=True, exist_ok=True)

    def iteration_folder(realization, iteration):
        return simulations / f"realisation-{realization}" / f"iter-{iteration}"

    def summary_dates(summary):
        return [
            summary.start_date + datetime.timedelta(days=float(day))
            for day in summary["TIME"]
        ]

    def get_training_index(dates):
        %if model_name=='drogon':
        return 0
        %else:
        return next((index for index, date in enumerate(dates) if date > training), len(dates))
        %endif

    def history_key(key):
        return key[:4] + "H" + key[4:]

    def normalized_squared_error(simulated, observed, quantity):
        sigma = max(minerr[quantity], var[quantity] * observed)
        return ((simulated - observed) / sigma) ** 2

    def read_simulation_time(path):
        try:
            with path.open("r", encoding="utf8") as stream:
                row = next(csv.reader(stream, delimiter=" "))
            return float(row[-1])
        except (OSError, StopIteration, ValueError, IndexError):
            return None

    def read_parameters(path, iteration):
        if num_realizations <= 1 or not path.exists():
            return
        data = np.genfromtxt(path, delimiter=" ")
        if np.size(data) == 0:
            return
        values = np.atleast_2d(data)[:, -1]
        expected = num_para * num_satn
        if len(values) != expected:
            raise ValueError(f"Expected {expected} parameters in {path}, found {len(values)}")
        counter = 0
        for parameter_index in range(num_para):
            for satnum_index in range(num_satn):
                param[iteration][parameter_index][satnum_index].append(values[counter])
                counter += 1

    def save_figure(fig, path):
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)

    def load_saturation_tables(folder):
        init_file = folder / "${reference_case_name}_COARSER.INIT"
        init = OpmFile(str(init_file))
        tabdims = init["TABDIMS"]
        iswof = tabdims[20]
        nswe = tabdims[21]
        nsatnum = tabdims[22]
        isgof = tabdims[23]
        isgofn = tabdims[26] + 2 * nswe * nsatnum + (nsatnum - 1) * (2 * nswe) + 2 * nswe + 2
        iswofn = tabdims[26] + 2 * nswe * nsatnum
        table = np.asarray(init["TAB"])
        table_length = (3 * nsatnum) * (nswe - 1) + (3 * nsatnum - 1)
        sgof = table[isgof - 1:isgof + table_length]
        swof = table[iswof - 1:iswof + table_length]
        sgof_kn = []
        swof_kn = []
        for satnum_index in range(nsatnum):
            start = isgofn - 3 + 2 * satnum_index * nswe
            values = table[start:start + 2 * nswe]
            averaged = np.mean(values.reshape(-1, 2), axis=1)
            averaged[0] = values[0]
            averaged[-1] = values[-1]
            sgof_kn.append(averaged)
            start = iswofn - 1 + 2 * satnum_index * nswe
            values = table[start:start + 2 * nswe]
            averaged = np.mean(values.reshape(-1, 2), axis=1)
            averaged[0] = values[0]
            averaged[-1] = values[-1]
            swof_kn.append(averaged)
        sgof = np.append(sgof, np.asarray(sgof_kn).ravel()).reshape(4, nsatnum, nswe)
        swof = np.append(swof, np.asarray(swof_kn).ravel()).reshape(4, nsatnum, nswe)
        return sgof, swof, nsatnum

    def plot_saturation_quantity(tables, satnum_index, title, xlabel, ylabel, filename, value_index, complementary=False):
        fig, ax = plt.subplots()
        labels = ["Single ensemble"] if len(tables) == 1 else ["Initial ensemble", "Final ensemble"]
        table_colors = [colors["final"]] if len(tables) == 1 else [colors["initial"], colors["final"]]
        for collection, label, color in zip(tables, labels, table_colors):
            for realization_index, table in enumerate(collection):
                saturation = table[0][satnum_index]
                valid = saturation < 1e19
                x_values = 1.0 - saturation[valid] if complementary else saturation[valid]
                ax.plot(x_values, table[value_index][satnum_index][valid], label=label if realization_index == 0 else None, color=color)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.legend()
        save_figure(fig, postprocessing / "saturation_functions" / filename)

    selected_iterations = [0] if num_iterations == 1 else [0, num_iterations - 1]
    saturation_sgof = []
    saturation_swof = []
    nsatnum = num_satn
    for iteration in selected_iterations:
        sgof_collection = []
        swof_collection = []
        for realization in range(num_realizations):
            folder = iteration_folder(realization, iteration)
            if (folder / "OK").exists():
                sgof, swof, nsatnum = load_saturation_tables(folder)
                sgof_collection.append(sgof)
                swof_collection.append(swof)
        saturation_sgof.append(sgof_collection)
        saturation_swof.append(swof_collection)
    if nsatnum < 100 and all(saturation_swof) and all(saturation_sgof):
        for satnum_index in range(nsatnum):
            plot_saturation_quantity(saturation_swof, satnum_index, "SWOF", "Water saturation [-]", "Krw [-]", f"swof_krw_satnum_{satnum_index}.png", 1)
            plot_saturation_quantity(saturation_swof, satnum_index, "SWOF", "Water saturation [-]", "Krow [-]", f"swof_krow_satnum_{satnum_index}.png", 3, complementary=True)
            plot_saturation_quantity(saturation_swof, satnum_index, "SWOF", "Water saturation [-]", "Pc [Bar]", f"swof_pc_satnum_{satnum_index}.png", 2)
            plot_saturation_quantity(saturation_sgof, satnum_index, "SGOF", "Gas saturation [-]", "Krg [-]", f"sgof_krg_satnum_{satnum_index}.png", 1)
            plot_saturation_quantity(saturation_sgof, satnum_index, "SGOF", "Gas saturation [-]", "Krog [-]", f"sgof_krog_satnum_{satnum_index}.png", 3, complementary=True)
            plot_saturation_quantity(saturation_sgof, satnum_index, "SGOF", "Gas saturation [-]", "Pc [Bar]", f"sgof_pc_satnum_{satnum_index}.png", 2)

    wells = {quantity: [] for quantity in well_types}
    var = dict(zip(well_types, [${observation_relative_errors[0]}, ${observation_relative_errors[1]}, ${observation_relative_errors[2]}]))
    minerr = dict(zip(well_types, [${observation_minimum_errors[0]}, ${observation_minimum_errors[1]}, ${observation_minimum_errors[2]}]))
    cum = {quantity: [[] for _ in range(num_iterations)] for quantity in well_types}
    fcum = {quantity: [[] for _ in range(num_iterations)] for quantity in field_types}
    rcum = {quantity: [] for quantity in well_types}
    rfcum = {quantity: [] for quantity in field_types}
    fmass = {quantity: 0.0 for quantity in field_types}
    param = [[[[] for _ in range(num_satn)] for _ in range(num_para)] for _ in range(num_iterations)]
    final_outputs = [[] for _ in range(num_realizations)]
    error_standard = 0.0
    error_ens = [[np.inf for _ in range(num_realizations)] for _ in range(num_iterations)]
    error_hist = [[] for _ in range(num_iterations)]
    time_ens = [[] for _ in range(num_iterations)]
    successful_realizations = [0 for _ in range(num_iterations)]
    initial_lines = []
    final_lines = []
    mean_time = 0.0
    num_cells_default = OpmGrid(str(pycopm_path / "reference_simulation" / "${model_name}" / "${reference_case_name}.EGRID")).active_cells
    num_cells_hm = OpmGrid(str(iteration_folder(0, 0) / "${reference_case_name}_COARSER.EGRID")).active_cells
    reference_base = pycopm_path / "reference_simulation" / "${model_name}" / "${reference_case_name}"
    with Path(f"{reference_base}.DBG").open("r", encoding="utf8") as stream:
        debug_rows = list(csv.reader(stream, delimiter=":"))
    time_standard = float(debug_rows[-23][-1])
    reference_summary = OpmSummary(f"{reference_base}.SMSPEC")
    well_names = []
    for key in reference_summary.keys():
        if key.startswith("W") and ":" in key and key.split(":")[-1] not in well_names:
            well_names.append(key.split(":")[-1])
    for quantity in well_types:
        field_quantity = field_by_well[quantity]
        density = densities[quantity]
        fmass[field_quantity] = density * reference_summary[field_quantity + "H"][-1]
        for well in well_names:
            key = f"{quantity}H:{well}"
            if np.sum(reference_summary[key]) > 0:
                wells[quantity].append(f"{quantity}:{well}")
    reference_dates = summary_dates(reference_summary)
    reference_training_index = get_training_index(reference_dates)
    for quantity in well_types:
        field_quantity = field_by_well[quantity]
        density = densities[quantity]
        rfcum[field_quantity].append(density * abs(reference_summary[field_quantity][-1] - reference_summary[field_quantity + "H"][-1]))
        rcum[quantity].append(0.0)
        for key in wells[quantity]:
            data = reference_summary[key]
            history = reference_summary[history_key(key)]
            rcum[quantity][-1] += density * np.sum(np.abs(data[reference_training_index:] - history[reference_training_index:]))
    observation_count = 0
    for quantity in ["WOPR", "WGPR", "WWPR"]:
        for key in wells[quantity]:
            data = reference_summary[key]
            history = reference_summary[history_key(key)]
            for simulated, observed in zip(data[reference_training_index:], history[reference_training_index:]):
                error_standard += normalized_squared_error(simulated, observed, quantity)
                observation_count += 1
    error_standard = error_standard / (2.0 * observation_count) if observation_count else np.nan

    for realization in range(num_realizations):
        for iteration in range(num_iterations):
            folder = iteration_folder(realization, iteration)
            if not (folder / "OK").exists():
                continue
            summary = OpmSummary(str(folder / "${reference_case_name}_COARSER.SMSPEC"))
            dates = summary_dates(summary)
            training_index = get_training_index(dates)
            total_error = 0.0
            count = 0
            collect_cumulative = iteration in selected_iterations
            if collect_cumulative:
                for quantity in well_types:
                    field_quantity = field_by_well[quantity]
                    density = densities[quantity]
                    fcum[field_quantity][iteration].append(density * abs(summary[field_quantity][-1] - summary[field_quantity + "H"][-1]))
                    cum[quantity][iteration].append(0.0)
            realization_lines = []
            for quantity in well_types:
                density = densities[quantity]
                for key in wells[quantity]:
                    data = summary[key]
                    history = summary[history_key(key)]
                    if iteration == 0 or iteration == num_iterations - 1:
                        realization_lines.append([dates, data])
                    for simulated, observed in zip(data[training_index:], history[training_index:]):
                        total_error += normalized_squared_error(simulated, observed, quantity)
                        if collect_cumulative:
                            cum[quantity][iteration][-1] += density * abs(simulated - observed)
                        count += 1
            if count:
                objective = total_error / (2.0 * count)
                error_ens[iteration][realization] = objective
                error_hist[iteration].append(objective)
            successful_realizations[iteration] += 1
            simulation_time = read_simulation_time(folder / "time_sim.txt")
            if simulation_time is not None:
                time_ens[iteration].append(simulation_time)
                if iteration == num_iterations - 1:
                    mean_time += simulation_time
            if iteration == 0:
                if not initial_lines:
                    initial_lines = realization_lines
                read_parameters(folder / "parameters.txt", iteration)
            if iteration == num_iterations - 1:
                if not final_lines:
                    final_lines = realization_lines
                final_outputs[realization] = realization_lines
                read_parameters(folder / "parameters.txt", iteration)
    if successful_realizations[-1] > 0:
        mean_time /= successful_realizations[-1]
    best_realizations = []
    for iteration in range(num_iterations):
        finite = np.isfinite(error_ens[iteration])
        best_realizations.append(int(np.argmin(error_ens[iteration])) if np.any(finite) else None)
    parameter_file = iteration_folder(0, 0) / "parameters.txt"
    csv_data = np.genfromtxt(parameter_file, delimiter=" ") if parameter_file.exists() else []

    plot_index = 0
    for quantity in well_types:
        for key in wells[quantity]:
            fig, ax = plt.subplots()
            best_final = best_realizations[-1]
            if num_realizations > 1 and num_iterations == 1 and final_lines:
                ax.plot(final_lines[plot_index][0], final_lines[plot_index][1], color=colors["final"], label="Ensemble")
                if best_final is not None and final_outputs[best_final]:
                    ax.plot(final_outputs[best_final][plot_index][0], final_outputs[best_final][plot_index][1], color=colors["closest"], lw=1.5, label="Closest to all obs")
            elif num_iterations > 1 and initial_lines and final_lines:
                ax.plot(initial_lines[plot_index][0], initial_lines[plot_index][1], color=colors["initial"], label="Initial ensemble")
                ax.plot(final_lines[plot_index][0], final_lines[plot_index][1], color=colors["final"], label="Final ensemble")
                if best_final is not None and final_outputs[best_final]:
                    ax.plot(final_outputs[best_final][plot_index][0], final_outputs[best_final][plot_index][1], color=colors["closest"], lw=1.5, label="Closest to all obs")
                ax.axvline(x=training, color="black", ls="--", lw=1)
            elif final_lines:
                ax.plot(final_lines[plot_index][0], final_lines[plot_index][1], color=colors["final"], label="Single run")
            data = reference_summary[key]
            history = reference_summary[history_key(key)]
            ax.plot(reference_dates, data, color="m", label="opm-tests")
            if np.sum(history > 0):
                errors = [max(minerr[quantity], var[quantity] * value) for value in history]
                ax.errorbar(reference_dates, history, yerr=errors, color=colors["data"], markersize=0.5, elinewidth=0.5, fmt="o", linestyle="", label="Data")
            ax.set_ylabel(f"{key} [SM3/day]", fontsize=12)
            ax.set_xlabel("Time [years]", fontsize=12)
            ax.xaxis.set_tick_params(size=6, rotation=45)
            ax.legend()
            ax.set_ylim(bottom=0)
            prefix = "HISTO_DATA_" if np.sum(history > 0) else ""
            save_figure(fig, postprocessing / "wells" / f"{prefix}{key[:4]}_{key[5:]}.png")
            plot_index += 1
    best_final = best_realizations[-1]
    source_folder = iteration_folder(0, 0) if num_realizations == 1 else iteration_folder(best_final, num_iterations - 1) if best_final is not None else None
    if source_folder is not None and source_folder.exists():
        shutil.copytree(source_folder, postprocessing / "closest_to_obs", dirs_exist_ok=True)
    %if len(cleanup_file_suffixes) > 0:
    for iteration in range(num_iterations):
        for realization in range(num_realizations):
            for suffix in [${cleanup_file_suffixes}]:
                for path in iteration_folder(realization, iteration).glob(f"*.{suffix}"):
                    path.unlink(missing_ok=True)
    %endif

    if any(error_hist):
        fig, ax = plt.subplots()
        available = [index for index, values in enumerate(error_hist) if values]
        ax.boxplot([error_hist[index] for index in available], positions=available)
        ax.axhline(y=error_standard, color="black", ls="--", lw=1, label="opm-tests")
        ax.set_title(r"$O_{i,j}=\frac{1}{2N_{obs}}\sum_n^{N_{obs}}((d^{n}_{i,j}-d^{n})/\sigma_n)^2$")
        ax.legend()
        ax.set_xlabel("# iteration [-]")
        ax.set_ylabel("Mismatch [-]")
        ax.set_xticks(range(num_iterations))
        save_figure(fig, postprocessing / "dist_mismatch.png")
        fig, ax = plt.subplots()
        tab20s = matplotlib.colormaps["tab20"]
        for iteration, values in enumerate(error_hist):
            if values:
                ax.plot(iteration, np.mean(values), markersize=10, marker="o", label=rf"$N_{{ens}}={successful_realizations[iteration]}$", color=tab20s.colors[iteration % len(tab20s.colors)])
        ax.axhline(y=error_standard, color="black", ls="--", lw=1, label=f"opm-tests (#Active cells: {num_cells_default})")
        ax.set_title(r"$O_i=\frac{1}{N_{ens}}\sum_{j}^{N_e}O_{i,j}$, " + f"#HM parameters: {len(csv_data)}, #Active cells: {num_cells_hm}")
        ax.legend()
        ax.set_xlabel("# iteration [-]")
        ax.set_ylabel("Mismatch [-]")
        ax.set_xticks(range(num_iterations))
        save_figure(fig, postprocessing / "hm_mismatch.png")
    if any(time_ens):
        fig, ax = plt.subplots()
        available = [index for index, values in enumerate(time_ens) if values]
        ax.boxplot([time_ens[index] for index in available], positions=available)
        ax.axhline(y=time_standard, color="black", ls="--", lw=1, label="opm-tests")
        ax.set_title(f"Total time of the HM: {datetime.timedelta(seconds=${'{0:.2f}'.format(elapsed_seconds)})}")
        ax.set_xlabel("# iteration [-]")
        ax.set_xticks(range(num_iterations))
        ax.set_ylabel("Simulation time [s]")
        ax.legend()
        save_figure(fig, postprocessing / "solverTime.png")

    if num_realizations > 1 and num_satn < 100:
        for parameter_index, parameter_name in enumerate(name_para):
            values = [param[-1][parameter_index][satnum_index] for satnum_index in range(num_satn)]
            available = [(index, item) for index, item in enumerate(values) if item]
            if not available:
                continue
            fig, ax = plt.subplots()
            ax.boxplot([item for _, item in available], positions=[index + 1 for index, _ in available])
            ax.set_title(f"Initial distribution: {dist_para[parameter_index]}")
            ax.set_xlabel("# satnum [-]")
            ax.set_ylabel("Final distribution [-]")
            save_figure(fig, postprocessing / "parameters" / f"final_parameter_distribution_{parameter_name}.png")

    bar_colors = ["b", "g", "r"]
    def plot_cumulative(data, reference, quantities, ylabel, filename, webviz_values, normalize=None, mass_labels=False):
        last_mean = np.nan
        for iteration, webviz_value in zip(selected_iterations, webviz_values):
            if not data[quantities[0]][iteration]:
                continue
            components = [np.asarray(data[quantity][iteration], dtype=float) for quantity in quantities]
            reference_components = [np.asarray(reference[quantity], dtype=float) for quantity in quantities]
            if normalize is not None:
                components = [values / normalize for values in components]
                reference_components = [values / normalize for values in reference_components]
            totals = np.sum(components, axis=0)
            reference_totals = np.sum(reference_components, axis=0)
            order = np.argsort(totals)
            sorted_components = [values[order] for values in components]
            sorted_totals = totals[order]
            last_mean = np.mean(sorted_totals)
            fig, ax = plt.subplots()
            suffix = " %" if normalize is not None else " kg" if mass_labels else ""
            ax.axhline(y=np.mean(reference_totals), color="black", ls="--", lw=1, label=f"opm-tests: {np.mean(reference_totals):.2f}{suffix}" if normalize is not None else f"opm-tests: {np.mean(reference_totals):.3e}{suffix}")
            %if model_name=='drogon':
            ax.axhline(y=webviz_value, color="black", ls=":", lw=1, marker="*", markevery=0.2, label=f"Mean (webviz): {webviz_value:.2f}{suffix}" if normalize is not None else f"Mean (webviz): {webviz_value:.3e}{suffix}")
            %endif
            ax.axhline(y=last_mean, color="black", ls="-", marker="o", markevery=0.2, lw=1, label=f"Mean (pycopm): {last_mean:.2f}{suffix}" if normalize is not None else f"Mean (pycopm): {last_mean:.3e}{suffix}")
            bottoms = np.zeros_like(sorted_totals)
            for index, (quantity, values) in enumerate(zip(quantities, sorted_components)):
                label = quantity + (f" ({fmass[quantity]:.3e} kg)" if mass_labels and normalize is not None else "")
                ax.bar(range(len(values)), values, bottom=bottoms, color=bar_colors[index], label=label)
                bottoms += values
            ax.set_title(f"Realization (iter-{iteration})")
            ax.set_ylabel(ylabel)
            ax.legend()
            save_figure(fig, postprocessing / f"{filename}_ite-{iteration}.png")
        return last_mean

    plot_cumulative(cum, rcum, well_types, "Cumulative mismatch", "cumulative_mismatch_rate", [8.502e8, 3.606e8])
    plot_cumulative(fcum, rfcum, field_types, "Cumulative final mass", "cumulative_mismatch_mass", [1.914e9, 4.903e8], mass_labels=True)
    total_mass = sum(fmass.values()) / 100.0
    normalized_mean = plot_cumulative(fcum, rfcum, field_types, "Cumulative final mass [%]", "cumulative_mismatch_mass_normalized", [19.06, 4.88], normalize=total_mass, mass_labels=True) if total_mass else np.nan
    goal = 4.88 - normalized_mean

    print(f"\nThe postprocessing files have been written to {postprocessing}")
    errors_file = postprocessing / "errors.txt"
    with errors_file.open("w", encoding="utf8") as stream:
        if num_realizations > 1:
            stream.write(f"Closest final realization to all obs: {best_final}\n")
            stream.write(f"Number of parameters to HM: {len(csv_data)}\n")
            stream.write(f"Mean simulation time of a single ensemble: {datetime.timedelta(seconds=mean_time)}\n")
            stream.write(f"Total execution time: {datetime.timedelta(seconds=${'{0:.2f}'.format(elapsed_seconds)})}\n")
            stream.write(f"Mismatch (standard simulation from opm-test deck): {error_standard:.4e}\n")
            for iteration in range(num_iterations):
                stream.write(f"Iteration {iteration}; Number of ensembles {successful_realizations[iteration]}\n")
                stream.write(f"Mismatch (mean): {np.mean(error_hist[iteration]) if error_hist[iteration] else np.nan:.4e}\n")
                best = best_realizations[iteration]
                best_error = error_ens[iteration][best] if best is not None else np.nan
                stream.write(f"Mismatch (closest realization to all obs): {best_error:.4e}\n")
        else:
            single_error = error_ens[0][0] if np.isfinite(error_ens[0][0]) else np.nan
            stream.write(f"Mismatch (standard simulation from opm-test deck): {error_standard:.4e}\n")
            stream.write(f"Mismatch (single simulation): {single_error:.4e}\n")
    print(errors_file.read_text(encoding="utf8"), end="")
    %if model_name=='drogon':
    print(f"Difference (webviz - pycopm): {goal:.2f} (a positive number (percentage) is the goal)")
    print(f"See {postprocessing}/cumulative_mismatch_mass_normalized_ite-{selected_iterations[-1]}.png\n")
    if goal <= 0:
        print("To improve the goal, for example, run a history-matching study (mode = 'ert') and increase the number")
        print("of ensembles (mep), iterations (--weights), distribution type/intervals, or change the random seed (rds).\n")
    %endif


if __name__ == "__main__":
    visualizeData()
