WHR="examples/decks"
OUT="test_outputs/docs_theory_transformations"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_plopm.sh
pycopm -i $WHR/THEORY1.DATA -o $OUT -p 1 -v "xypolygon [50,90] [60,60] [90,60] [65,40] [75,10] [50,30] [25,10] [35,40] [10,60] [40,60] [50,90]" -m all
pycopm -i $OUT/THEORY1_PYCOPM.DATA -o $OUT -d 'rotatexy 45' -m all
pycopm -i $OUT/THEORY1_PYCOPM_PYCOPM.DATA -o $OUT -d 'scale [1,0.25,1]' -m all
plopm -i "$OUT/THEORY1_PYCOPM_PYCOPM $OUT/THEORY1_PYCOPM_PYCOPM_PYCOPM" -c nipy_spectral -v index_j -s ,,1 -o $OUT -cnum 5 -d 12,6 -subfigs 1,2 -t "ROTATED  ROTATED AND SCALED" -suptitle 0 -cbsfax 0.20,0.001,0.6,0.02 -save transformation_plopm
