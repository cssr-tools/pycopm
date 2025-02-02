# SPDX-FileCopyrightText: 2025 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the generic submodel functionality"""

import os
import pathlib
import subprocess
import numpy as np
from resdata.resfile import ResdataFile

dirname: pathlib.Path = pathlib.Path(__file__).parent


def test_submodel():
    """See decks/MODEL0.DATA and decks/MODEL1.DATA"""
    for i in range(2):
        os.chdir(f"{dirname}/decks")
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"MODEL{i}.DATA",
                "-o",
                "submodel",
                "-g",
                "4,4,3",
                "-m",
                "all",
                "-w",
                f"MODEL{i}_FINER",
                "-l",
                "FINER",
            ],
            check=True,
        )
        assert os.path.exists(f"{dirname}/decks/submodel/MODEL{i}_FINER.INIT")
        assert os.path.exists(f"{dirname}/decks/submodel/MODEL{i}_FINER.EGRID")
        os.chdir(f"{dirname}/decks/submodel")
        for j in [1, 3, 4]:
            subprocess.run(
                [
                    "pycopm",
                    "-i",
                    f"MODEL{i}_FINER.DATA",
                    "-o",
                    ".",
                    "-v",
                    "xypolygon [3,7.5] [7.5,3] [12,7.5] [7.5,12] [3,7.5]",
                    "-m",
                    "all",
                    "-w",
                    f"MODEL{i}_FINER_SUBMODEL",
                    "-l",
                    "SUBMODEL",
                    "-p",
                    f"{j}",
                ],
                check=True,
            )
            porv = np.array(
                ResdataFile(f"MODEL{i}_FINER_SUBMODEL.INIT").iget_kw("PORV")[0]
            )
            assert abs(sum(porv) - 150) < 1e-6
            assert sum(porv > 0) == 21
