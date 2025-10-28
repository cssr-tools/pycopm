# SPDX-FileCopyrightText: 2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic refinement functionality"""

import os
import pathlib
import subprocess
import numpy as np
from resdata.resfile import ResdataFile

mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]
testpth: pathlib.Path = pathlib.Path(__file__).parent


def test_refinement(flow):
    """See examples/decks/MODEL2.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    for use in ["opm", "resdata"]:
        sub = f"FINER{use.upper()}"
        subprocess.run(
            [
                "pycopm",
                "-f",
                flow,
                "-i",
                f"{mainpth}/examples/decks/MODEL2.DATA",
                "-o",
                f"{testpth}/output/finer",
                "-g",
                "2,4,8",
                "-l",
                sub,
                "-w",
                sub,
                "-m",
                "all",
                "-u",
                use,
                "-warnings",
                "1",
            ],
            check=True,
        )
        assert os.path.exists(f"{testpth}/output/finer/{sub}.INIT")
        assert os.path.exists(f"{testpth}/output/finer/{sub}.EGRID")
        os.chdir(f"{testpth}/output/finer")
        porv = np.array(ResdataFile(f"{sub}.INIT").iget_kw("PORV")[0])
        assert abs(sum(porv) - 6506.25) < 1e-4
        assert sum(porv > 0) == 2430
