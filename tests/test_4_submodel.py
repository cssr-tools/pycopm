# SPDX-FileCopyrightText: 2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic submodel functionality"""

import os
import pathlib
import subprocess
import warnings
import numpy as np
from resdata.resfile import ResdataFile

has_opm = False
try:
    has_opm = bool(__import__("opm"))
except ImportError:
    warnings.warn(
        UserWarning(
            "The optional OPM Python package for postprocessing "
            "the simulation files is not found; then, test_4_submodel.py is only run "
            "using resdata."
        )
    )

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_submodel(flow):
    """See examples/decks/MODEL0.DATA and MODEL1.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    readers = ["resdata"]
    if has_opm:
        readers += ["opm"]
    for use in readers:
        for i in range(2):
            sub = f"MODEL{i}_FINER{use.upper()}"
            os.chdir(f"{testpth}/output")
            subprocess.run(
                [
                    "pycopm",
                    "-f",
                    flow,
                    "-i",
                    f"{mainpth}/examples/decks/MODEL{i}.DATA",
                    "-o",
                    f"{testpth}/output/submodel",
                    "-g",
                    "4,4,3",
                    "-warnings",
                    "1",
                    "-m",
                    "all",
                    "-w",
                    sub,
                    "-l",
                    sub,
                    "-u",
                    use,
                ],
                check=True,
            )
            assert os.path.exists(f"{testpth}/output/submodel/{sub}.INIT")
            assert os.path.exists(f"{testpth}/output/submodel/{sub}.EGRID")
            os.chdir(f"{testpth}/output/submodel")
            for j in [1, 3, 4]:
                subprocess.run(
                    [
                        "pycopm",
                        "-f",
                        flow,
                        "-i",
                        f"{sub}.DATA",
                        "-o",
                        ".",
                        "-v",
                        "xypolygon [3,7.5] [7.5,3] [12,7.5] [7.5,12] [3,7.5]",
                        "-m",
                        "all",
                        "-w",
                        f"{sub}SUBMODEL",
                        "-l",
                        f"{sub}SUBMODEL",
                        "-warnings",
                        "1",
                        "-p",
                        f"{j}",
                        "-u",
                        use,
                    ],
                    check=True,
                )
                porv = np.array(ResdataFile(f"{sub}SUBMODEL.INIT").iget_kw("PORV")[0])
                assert abs(sum(porv) - 150) < 1e-6
                assert sum(porv > 0) == 21
