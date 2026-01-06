# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic submodel functionality"""

import os
import pathlib
import subprocess
import numpy as np
from opm.io.ecl import EclFile as OpmFile

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_submodel(flow):
    """See examples/decks/MODEL0.DATA and MODEL1.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    for i in range(2):
        sub = f"MODEL{i}_FINER"
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
                "-m",
                "all",
                "-w",
                sub,
                "-l",
                sub,
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
                    "-p",
                    f"{j}",
                ],
                check=True,
            )
            porv = np.array(OpmFile(f"{sub}SUBMODEL.INIT")["PORV"])
            assert abs(np.sum(porv) - 150) < 1e-6
            assert np.sum(porv > 0) == 21
