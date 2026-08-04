WHR="examples/decks"
OUT="test_outputs/docs_theory_refinements"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_plopm.sh
pycopm -i $WHR/MODEL3.DATA -o $OUT -g 2,2,2 -m all
plopm -i "$OUT/MODEL3_PREP_PYCOPM_DRYRUN $OUT/MODEL3_PYCOPM" -v wells -xunits km -yunits km -yformat .0f -xformat .0f -ylnum 5 -xlnum 5 -s ,,: -grid black,1e-2 -subfigs 1,2 -o $OUT -d 10,4 -delax 1 -suptitle 0 -cbsfax 0.1,0.95,0.8,0.02 -t "Input grid  Refined grid" -save refinement_plopm
