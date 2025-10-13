# SPDX-FileCopyrightText: 2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801,R0914

"""Test the coarsening by transmissibilities"""

import os
import pathlib
import subprocess
import warnings
from resdata.resfile import ResdataFile

has_opm = False
try:
    has_opm = bool(__import__("opm"))
except ImportError:
    warnings.warn(
        UserWarning(
            "The optional OPM Python package for postprocessing "
            "the simulation files is not found; then, test_7_transmissibilities.py is only run "
            "using resdata."
        )
    )

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_transmissibilities(flow):
    """See examples/decks/MODEL4.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    subprocess.run(
        [
            flow,
            f"{mainpth}/examples/decks/MODEL4.DATA",
            f"--output-dir={testpth}/output/transmissibilities",
        ],
        check=True,
    )
    readers = ["resdata"]
    if has_opm:
        readers += ["opm"]
    values = [
        [523.75178, 706.33996, 5008.1327, 106.21933],
        [523.75178, 706.33996, 0, 106.21933],
    ]
    for use in readers:
        for i, m in enumerate(["1", "2"]):
            sub = use.upper() + m
            subprocess.run(
                [
                    "pycopm",
                    "-f",
                    flow,
                    "-o",
                    f"{testpth}/output/transmissibilities",
                    "-i",
                    f"{mainpth}/examples/decks/MODEL4.DATA",
                    "-z",
                    "1:30,31:56,57:111,112:116,117:217",
                    "-w",
                    f"COARSER{sub}",
                    "-l",
                    f"C0{sub}",
                    "-t",
                    m,
                    "-a",
                    "max",
                    "-m",
                    "all",
                    "-u",
                    use,
                ],
                check=True,
            )
            init = ResdataFile(f"{testpth}/output/transmissibilities/COARSER{sub}.INIT")
            for j, n in enumerate(["X", "Y", "Z", "NNC"]):
                assert (
                    abs(sum(init.iget_kw(f"TRAN{n}")[0]) - values[i][j]) < 1e-2
                ), f"Issue in TRAN{n} with -u {use} -t {i}"
