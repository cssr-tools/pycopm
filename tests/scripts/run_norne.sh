. tests/scripts/initialize_output_folders.sh
WHR="test_outputs/opm-data/norne/NORNE_ATW2013"
INC="test_outputs/opm-data/norne/INCLUDE"
if [ ! -f "$WHR.UNRST" ]; then
  mpirun -np 8 flow $WHR.DATA
  in="$WHR.DATA"
  tmp="${in}.tmp"

  for f in FAULT/FAULT_JUN_05.INC BC0407_HIST01122006.SCH; do
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
