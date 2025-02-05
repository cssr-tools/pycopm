% if dic['mode'] in ["files","single-run"]:
NUM_REALIZATIONS 1
MIN_REALIZATIONS 1
% else :
NUM_REALIZATIONS ${dic['net']}
MIN_REALIZATIONS ${dic['mrn']}
% endif

MAX_RUNTIME ${dic['mrt']}

QUEUE_SYSTEM LOCAL
QUEUE_OPTION LOCAL MAX_RUNNING ${dic['mep']}

% if dic['rds'] > 0:
RANDOM_SEED ${dic['rds']}
% endif

RUNPATH output/simulations/realisation-<IENS>/iter-<ITER>
ENSPATH output/storage

ECLBASE ${dic['name']}_COARSER
RUN_TEMPLATE preprocessing/${dic['name']}_COARSER.DATA <ECLBASE>.DATA

% if dic['rock'][0][1] > 0 and dic['mode'] in ["files","ert"]:
GEN_KW PERMX ./parameters/PERMX.tmpl PERMX.json ./parameters/PERMX_priors.data
% endif
% if dic['rock'][1][1] > 0 and dic['mode'] in ["files","ert"]:
GEN_KW PERMY ./parameters/PERMY.tmpl PERMY.json ./parameters/PERMY_priors.data
% endif
% if dic['rock'][2][1] > 0 and dic['mode'] in ["files","ert"]:
GEN_KW PERMZ ./parameters/PERMZ.tmpl PERMZ.json ./parameters/PERMZ_priors.data
% endif
% if dic['indc'] >0:
% for i in range(len(dic['LET'])):
% if dic['LET'][i][2] > 0:
GEN_KW COEFF${dic['LET'][i][0]} ./parameters/coeff_${dic['LET'][i][0]}.tmpl coeff_${dic['LET'][i][0]}.json ./parameters/coeff_${dic['LET'][i][0]}_priors.data
% endif
% endfor
% endif

% if dic['mode'] in ["files","ert"]:
REFCASE ${dic['case']+'_HISTORY'}
OBS_CONFIG ./observations/${dic['obs']}.data
% endif

% if dic['rock'][0][1] > 0 and dic['mode'] in ["files","ert"]:
INSTALL_JOB permx_eval ./jobs/PERMX_EVAL
FORWARD_MODEL permx_eval
% endif
% if dic['rock'][1][1] > 0 and dic['mode'] in ["files","ert"]:
INSTALL_JOB permy_eval ./jobs/PERMY_EVAL
FORWARD_MODEL permy_eval
% endif
% if dic['rock'][2][1] > 0 and dic['mode'] in ["files","ert"]:
INSTALL_JOB permz_eval ./jobs/PERMZ_EVAL
FORWARD_MODEL permz_eval
% endif
% if dic['indc'] > 0:
INSTALL_JOB table_eval ./jobs/TABLE_EVAL
FORWARD_MODEL table_eval
% endif

% if dic['mode'] in ["files","ert"]:
INSTALL_JOB flow_eval ./jobs/FLOW_EVAL
FORWARD_MODEL flow_eval

INSTALL_JOB time_eval ./jobs/TIME_EVAL
FORWARD_MODEL time_eval
%endif