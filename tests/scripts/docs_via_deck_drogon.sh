. tests/scripts/get_opm_tests.sh
OUT="test_outputs/docs_via_deck_drogon"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/run_drogon.sh
WHR="test_outputs/opm-tests/drogon/model"
pycopm -i $WHR/DROGON_HIST.DATA -c 1,1,3 -p 1 -q 1 -l C1 -o $WHR
pycopm -i $WHR/DROGON_HIST_PYCOPM.DATA -c 1,3,1 -p 1 -q 1 -j 2.5 -l C2 -m all -o $WHR
pycopm -i $WHR/DROGON_HIST.DATA -c 2,2,2 -p 1 -q 1 -j 4 -w DROGON_2TIMES_COARSER -m all -o $WHR
flow $WHR/DROGON_HIST_PYCOPM_PYCOPM.DATA
flow $WHR/DROGON_2TIMES_COARSER
plopm -i "$WHR/DROGON_HIST $WHR/DROGON_HIST_PYCOPM_PYCOPM" -o $OUT -v poro -subfigs 1,2 -save drogon_generic_plopm -s ,,: -rotate '-30' -xunits km -yunits km -xformat .1f -yformat .1f -d 11,8 -delax 1 -suptitle 0 -cbsfax 0.1,0.95,0.8,0.02 -cnum 5 -cformat .2f -t "Drogon  Coarsened Drogon" -f 17 -xlnum 2 -ylnum 2
plopm -i "$WHR/DROGON_HIST $WHR/DROGON_HIST_PYCOPM_PYCOPM $WHR/DROGON_2TIMES_COARSER" -o $OUT -v 'FOIP,FOPR,TCPU' -tunits y -f 14 -subfigs 2,2 -delax 1 -loc empty,empty,empty,center -d 10,5 -xformat '.1f' -xlnum 6 -ylabel 'sm$^3$  sm$^3$/day  seconds' -t 'Field oil in place  Field oil production rate  Simulation time' -labels 'DROGON  DROGON 3XZ COARSER  DROGON 2XYZ COARSER' -save drogon_pycopm_comparison -yformat '.2e,.0f,.0f'
plopm -i "$WHR/DROGON_HIST $WHR/DROGON_HIST_PYCOPM_PYCOPM $WHR/DROGON_2TIMES_COARSER" -o $OUT -v sgas -subfigs 1,3  -d 15,11 -cnum 5 -m gif -xlnum 4 -ylnum 4 -dpi 300 -t "DROGON  DROGON 3XZ COARSER  DROGON 2XYZ COARSER" -f 16 -interval 2000 -loop 1 -cformat .2f -cbsfax 0.15,0.93,0.7,0.02 -s ,,1 -rotate '-30' -xunits km -yunits km -xformat .0f -yformat .0f -c cet_rainbow_bgyrm_35_85_c69 -delax 1 -tunits tstep
