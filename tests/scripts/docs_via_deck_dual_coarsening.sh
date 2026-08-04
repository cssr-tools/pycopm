WHR="examples/decks/MODEL6.DATA"
OUT="test_outputs/docs_via_deck_dual_coarsening"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_plopm.sh
pycopm -i $WHR -o $OUT -z 1:4 -w STANDARD -l S -t 2 -a max
pycopm -i $WHR -o $OUT -z 1:4 -w DUAL -dual 'poro <= 0.1' -l D -t 2 -a max
flow $WHR --output-dir=$OUT
flow $OUT/STANDARD.DATA
flow $OUT/DUAL.DATA
plopm -i "$OUT/MODEL6 $OUT/STANDARD $OUT/DUAL" -v 'pressure - 0pressure' -subfigs 1,3 -delax 1 -cbsfax 0.1,0.95,0.8,0.02 -d 12,4  -suptitle 0 -z 0 -clabel 'Pressure increase end of simulation [bar]' -grid 'black,1e-2' -o $OUT
