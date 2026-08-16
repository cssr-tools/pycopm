. tests/scripts/initialize_output_folders.sh &
. tests/scripts/get_plopm.sh &
wait

. tests/scripts/get_opm_data.sh &
. tests/scripts/get_opm_tests.sh &
wait

. tests/scripts/run_drogon.sh &
. tests/scripts/run_norne.sh &
wait

. tests/scripts/docs_config_views.sh &
. tests/scripts/docs_theory_coarsening.sh &
. tests/scripts/docs_theory_refinements.sh &
. tests/scripts/docs_theory_submodels.sh &
. tests/scripts/docs_theory_transformations.sh &
. tests/scripts/docs_via_config_drogon.sh &
. tests/scripts/docs_via_deck_drogon.sh &
. tests/scripts/docs_via_deck_dual_coarsening.sh &
. tests/scripts/docs_via_deck_hello_world.sh &
. tests/scripts/docs_via_deck_norne.sh &
. tests/scripts/docs_via_deck_smeaheia.sh &
. tests/scripts/docs_via_deck_spe10.sh &
wait

. tests/scripts/docs_check_outputs.sh
