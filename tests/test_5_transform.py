# SPDX-FileCopyrightText: 2025 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the generic submodel functionality"""

import os
import pathlib
import subprocess
from resdata.grid import Grid

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_transform():
    """See examples/decks/MODEL0.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    flags = ["translate", "scale", "rotatexy", "rotatexz", "rotateyz"]
    values = ["[5,-3,2]", "[2,.5,4]", "45", "-10", "15"]
    checks = [3, 4, 1, 3.5899, 4.848]
    for flag, val, check in zip(flags, values, checks):
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"{mainpth}/examples/decks/MODEL0.DATA",
                "-o",
                f"{testpth}/output/transform",
                "-d",
                f"{flag} {val}",
                "-m",
                "all",
                "-w",
                f"{flag.upper()}",
                "-l",
                f"{flag.upper()}",
            ],
            check=True,
        )
        assert os.path.exists(f"{testpth}/output/transform/{flag.upper()}.INIT")
        assert os.path.exists(f"{testpth}/output/transform/{flag.upper()}.EGRID")
        grid = Grid(f"{testpth}/output/transform/{flag.upper()}.EGRID")
        zcoord = grid.export_corners(grid.export_index())[-1][-1]
        assert abs(zcoord - check) < 1e-2
