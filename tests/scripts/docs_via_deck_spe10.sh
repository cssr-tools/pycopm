OUT="test_outputs/docs_via_deck_spe10"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_opm_data.sh
WHR="test_outputs/opm-data/spe10model2"
pycopm -i $WHR/SPE10_MODEL2.DATA -o $WHR -s pvmean -c 4,8,2 -m all
pycopm -i $WHR/SPE10_MODEL2_PYCOPM.DATA -o $WHR -p 0 -v 'INJ diamondxy 5' -m all -w vicinity -l sub -m all
plopm -i "$WHR/SPE10_MODEL2_PREP_PYCOPM_DRYRUN $WHR/SPE10_MODEL2_PYCOPM $WHR/VICINITY" -v poro -suptitle 0 -o $OUT -s ,,: -d 19.5,10 -cformat .2f -cnum 5 -subfigs 1,3 -delax 0 -cbsfax 0.20,0.001,0.6,0.02 -t "SPE10 MODEL2  COARSENED MODEL  SECTOR MODEL (FROM COARSENED MODEL)" -save spe10_plopm -f 20 -cbsfax 0.15,0.95,0.7,0.02
