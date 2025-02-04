# SPDX-FileCopyrightText: 2025 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the generic refinement functionality"""

import os
import pathlib
import subprocess
import numpy as np
from resdata.resfile import ResdataFile

mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]
testpth: pathlib.Path = pathlib.Path(__file__).parent


def test_refinement():
    """See examples/decks/MODEL2.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    subprocess.run(
        [
            "pycopm",
            "-i",
            f"{mainpth}/examples/decks/MODEL2.DATA",
            "-o",
            f"{testpth}/output/finer",
            "-g",
            "2,4,8",
            "-w",
            "FINER",
            "-m",
            "all",
        ],
        check=True,
    )
    assert os.path.exists(f"{testpth}/output/finer/FINER.INIT")
    assert os.path.exists(f"{testpth}/output/finer/FINER.EGRID")
    os.chdir(f"{testpth}/output/finer")
    porv = np.array(ResdataFile("FINER.INIT").iget_kw("PORV")[0])
    assert abs(sum(porv) - 6506.25) < 1e-4
    assert sum(porv > 0) == 2430
