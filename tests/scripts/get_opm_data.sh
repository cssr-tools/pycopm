if [ ! -d "test_outputs/opm-data" ]; then
  git clone --single-branch --depth 1 https://github.com/OPM/opm-data.git test_outputs/opm-data
fi
