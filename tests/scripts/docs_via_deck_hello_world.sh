WHR="examples/decks/HELLO_WORLD"
OUT="test_outputs/docs_via_deck_hello_world"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_plopm.sh
pycopm -i $WHR.DATA -o $OUT -c 5,5,1 -m all -l f1 -a max
plopm -i $OUT/HELLO_WORLD_PREP_PYCOPM_DRYRUN -v porv -o $OUT -s ,,1 -grid 'black,1e-2' -save hello_world_1_left
plopm -i $OUT/HELLO_WORLD_PYCOPM -v porv -o $OUT -s ,,1 -grid 'black,1e-2' -save hello_world_1_right
plopm -i "$OUT/HELLO_WORLD_PREP_PYCOPM_DRYRUN $OUT/HELLO_WORLD_PYCOPM" -v fipnum -s ,,1 -grid 'black,1e-2' -subfigs 1,2 -d 16,8 -delax 1 -suptitle 0 -cbsfax 0.1,0.95,0.8,0.02 -o $OUT -c cet_glasbey_hv -save hello_world_2 -t "Input model  Coarsened model" -f 20
pycopm -i $WHR.DATA -v 'xypolygon [4,8.5] [4,16.5] [11.5,16.5] [11.5,8.5]' -p 1 -m all -o $OUT -l f2
pycopm -i $OUT/HELLO_WORLD_PYCOPM.DATA -rx 0,0,0,2,0,0,0 -ry 0,0,0,2,0,0,0 -m all -o $OUT -l f3
pycopm -i $OUT/HELLO_WORLD_PYCOPM_PYCOPM.DATA -d 'rotatexy 45' -m all -o $OUT -l f4
plopm -i $OUT/HELLO_WORLD_PYCOPM -v porv -o $OUT -s ,,1 -grid 'black,1e-2' -save submodel -save hello_world_3_submodel
plopm -i $OUT/HELLO_WORLD_PYCOPM_PYCOPM -v porv -o $OUT -s ,,1 -grid 'black,1e-2' -save hello_world_3_submodel_refined
plopm -i $OUT/HELLO_WORLD_PYCOPM_PYCOPM_PYCOPM -v porv -o $OUT -s ,,1 -grid 'black,1e-2' -save hello_world_3_submodel_refined_rotated
