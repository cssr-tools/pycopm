WHR="examples/configurations/drogon/input.toml"
OUT="test_outputs/docs_via_config_drogon"
REF="src/pycopm/reference_simulation/drogon/DROGON"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_plopm.sh
pycopm -i $WHR -o $OUT
plopm -i "$REF $OUT/postprocessing/closest_to_obs/DROGON_COARSER" -v soil -xlnum 4 -ylnum 4 -cnum 5 -subfigs 1,2 -d 10,7 -delax 1 -cbsfax 0.1,0.95,0.8,0.02 -suptitle 0 -clabel 'Initial pore-volume weighted oil saturation [-]' -s ,,: -rotate -30 -xunits km -yunits km -xformat .0f -yformat .1f -o $OUT -r 0 -save drogon_coarser_plopm
