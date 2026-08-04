WHR="test_outputs/smeaheia/Simulation_Models/data/Statoil_Feasibility_sim_model_with_depletion_KROSS_INJ_SECTOR_20.DATA"
OUT="test_outputs/docs_via_deck_smeaheia"
if ! python -c "import playwright" >/dev/null 2>&1; then
    pip install playwright
    playwright install chromium
fi
if [ ! -f "$WHR" ]; then
    python3 tests/scripts/get_smeaheia.py
fi
. tests/scripts/initialize_output_folders.sh $OUT
pycopm -i $WHR -c 5,4,1 -a min -m all -o $OUT
plopm -i "$OUT/STATOIL_FEASIBILITY_SIM_MODEL_WITH_DEPLETION_KROSS_INJ_SECTOR_20_PREP_PYCOPM_DRYRUN $OUT/STATOIL_FEASIBILITY_SIM_MODEL_WITH_DEPLETION_KROSS_INJ_SECTOR_20_PYCOPM" -cnum 7 -s ,,1 -v poro -subfigs 1,2 -save smeaheia -t 'Smeaheia  Coarsened Smeaheia' -delax 1 -xunits km -xformat .0f -yunits km -yformat .0f -d 10,7 -suptitle 0 -c cet_rainbow_bgyrm_35_85_c69 -cbsfax 0.1,0.95,0.8,0.02 -cformat .2f -o $OUT -save smeaheia
