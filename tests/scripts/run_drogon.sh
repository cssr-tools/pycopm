. tests/scripts/initialize_output_folders.sh
WHR="test_outputs/opm-tests/drogon/model/DROGON_HIST"
INC="test_outputs/opm-tests/drogon/include"
if [ ! -f "$WHR.UNRST" ]; then
  mpirun -np 8 flow $WHR.DATA
  in="$WHR.DATA"
  tmp="${in}.tmp"
  sed -i.bak 's|NEWTRAN|MAPAXES\n4.5606369E+05 5.9394410E+06 4.5606369E+05 5.9265510E+06 4.6748934E+05 5.9265510E+06 /|g' $WHR.DATA && rm -f $WHR.DATA.bak
  for f in grid/drogon.faults schedule/drogon_hist.sch; do
    inc="$INC/$f"
    name="$(basename "$f" | sed 's/\./\\./g')"

    sed "/^INCLUDE$/{
    N
    /$name/{
    r $inc
    d
    }
    }" "$in" > "$tmp" && mv "$tmp" "$in"
  done
fi
