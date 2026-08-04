WHR="examples/decks"
OUT="test_outputs/docs_theory_coarsening"
. tests/scripts/initialize_output_folders.sh $OUT
. tests/scripts/get_plopm.sh
pycopm -i $WHR/THEORY0.DATA -o $OUT -c 3,1,3 -m all -a max -w coarsening_max_two_cells 
pycopm -i $WHR/THEORY0.DATA -o $OUT -c 3,1,3 -m all -a min -w coarsening_min_two_cells
pycopm -i $WHR/THEORY0.DATA -o $OUT -c 6,1,3 -m all -a max -w coarsening_max_one_cell
plopm -i "$OUT/THEORY0_PREP_PYCOPM_DRYRUN $OUT/COARSENING_MAX_TWO_CELLS $OUT/COARSENING_MIN_TWO_CELLS $OUT/COARSENING_MAX_ONE_CELL" -v fipnum -subfigs 1,4 -o $OUT -d 15,4 -clabel "Number of cell" -delax 1 -suptitle 0 -cbsfax 0.1,0.95,0.8,0.02 -t "Input grid (18 cells, 17 active cells)  Coarsening into two cells (using mode/max)  Coarsening into two cells (using min)  Coarsening into one cell (using mode/max)" -f 10 -save coarsening_plopm
