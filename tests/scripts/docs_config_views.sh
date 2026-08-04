WHR="src/pycopm/reference_simulation/norne/NORNE_ATW2013"
OUT="test_outputs/docs_config_views"
. tests/scripts/initialize_output_folders.sh $OUT
plopm -i "$WHR $WHR $WHR" -v "index_i,index_j,index_k" -o $OUT -s ',,: ,,: ,:,' -remove 0,0,0,1 -c cet_glasbey -cnum 5 -subfigs 1,3 -z 0 -clabel "Index [-]" -d 18,10 -xunits km -yunits km -xformat .1f -yformat .1f -suptitle 0 -cbsfax 0.1,0.95,0.8,0.02 -x '[455.5e3,463e3] [455.5e3,463e3] [453.2e3,454.8e3]' -y '[7319.5e3,7327e3] [7319.5e3,7327e3] [3.22e3,2.8e3]' -t "Index I  Index J  Index K" -save index_plopm