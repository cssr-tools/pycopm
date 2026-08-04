OUT="test_outputs/docs_via_deck_norne"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_opm_data.sh
. tests/scripts/run_norne.sh
WHR="test_outputs/opm-data/norne"
pycopm -i $WHR/NORNE_ATW2013.DATA -o $WHR -s pvmean -x 0,2,0,2,2,0,2,0,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,0,2,0,2,2,0,2,2,0,2,2,2,2,0 -y 0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,2,2,2,2,2,2,2,2,0 -z 0,0,2,0,0,2,2,2,2,2,0,2,2,2,2,2,0,0,2,0,2,2,0 -a min -p 1 -q 1 -m all
mpirun -np 8 flow $WHR/NORNE_ATW2013_PYCOPM
plopm -i "$WHR/NORNE_ATW2013 $WHR/NORNE_ATW2013_PYCOPM $WHR/NORNE_ATW2013 $WHR/NORNE_ATW2013_PYCOPM" -v sgas -o $OUT -s ,,: -rotate 65 -translate '[6456335.5,-3476500]' -x '[0,5600]' -y '[0,8800]' -d 30,10 -subfigs 1,4 -delax 1 -r 0,0,241,241 -suptitle 0 -cbsfax 0.15,0.95,0.7,0.02 -f 22 -t "Norne (intial time)  Coarsened Norne (initial time)  Norne (final time)  Coarsened Norne (final time)" -cnum 5 -cformat .2f -save norne_plopm
