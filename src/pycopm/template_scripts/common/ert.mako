% if execution_mode in ["files","single-run"]:
NUM_REALIZATIONS 1
MIN_REALIZATIONS 1
% else :
NUM_REALIZATIONS ${ensemble_size}
MIN_REALIZATIONS ${min_successful_realizations}
% endif

MAX_RUNTIME ${max_realization_runtime_seconds}

QUEUE_SYSTEM LOCAL
QUEUE_OPTION LOCAL MAX_RUNNING ${max_parallel_realizations}

% if random_seed > 0:
RANDOM_SEED ${random_seed}
% endif

RUNPATH output/simulations/realisation-<IENS>/iter-<ITER>
ENSPATH output/storage

ECLBASE ${reference_case_name}_COARSER
DATA_FILE preprocessing/${reference_case_name}_COARSER.DATA

% if rock_property_settings[0][1] > 0 and execution_mode in ["files","ert"]:
GEN_KW PERMX ./parameters/PERMX.tmpl PERMX.json ./parameters/PERMX_priors.data
% endif
% if rock_property_settings[1][1] > 0 and execution_mode in ["files","ert"]:
GEN_KW PERMY ./parameters/PERMY.tmpl PERMY.json ./parameters/PERMY_priors.data
% endif
% if rock_property_settings[2][1] > 0 and execution_mode in ["files","ert"]:
GEN_KW PERMZ ./parameters/PERMZ.tmpl PERMZ.json ./parameters/PERMZ_priors.data
% endif
% if use_let_tables:
% for i in range(len(let_parameters)):
% if let_parameters[i][2] > 0:
GEN_KW COEFF${let_parameters[i][0]} ./parameters/coeff_${let_parameters[i][0]}.tmpl coeff_${let_parameters[i][0]}.json ./parameters/coeff_${let_parameters[i][0]}_priors.data
% endif
% endfor
% endif

% if execution_mode in ["files","ert"]:
REFCASE ${f"{resource_directory}/reference_simulation/{model_name}/{reference_case_name}_HISTORY"}
OBS_CONFIG ./observations/observations.data
% endif

% if rock_property_settings[0][1] > 0 and execution_mode in ["files","ert"]:
INSTALL_JOB permx_eval ./jobs/PERMX_EVAL
FORWARD_MODEL permx_eval
% endif
% if rock_property_settings[1][1] > 0 and execution_mode in ["files","ert"]:
INSTALL_JOB permy_eval ./jobs/PERMY_EVAL
FORWARD_MODEL permy_eval
% endif
% if rock_property_settings[2][1] > 0 and execution_mode in ["files","ert"]:
INSTALL_JOB permz_eval ./jobs/PERMZ_EVAL
FORWARD_MODEL permz_eval
% endif
% if use_let_tables:
INSTALL_JOB table_eval ./jobs/TABLE_EVAL
FORWARD_MODEL table_eval
% endif

% if execution_mode in ["files","ert"]:
INSTALL_JOB flow_eval ./jobs/FLOW_EVAL
FORWARD_MODEL flow_eval

INSTALL_JOB time_eval ./jobs/TIME_EVAL
FORWARD_MODEL time_eval
%endif
