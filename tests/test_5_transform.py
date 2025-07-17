# SPDX-FileCopyrightText: 2025 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic affine transformation functionality"""

import os
import pathlib
import subprocess
import warnings
from resdata.grid import Grid

OPM = False
try:
    OPM = bool(__import__("opm"))
except ImportError:
    warnings.warn(
        UserWarning(
            "The optional OPM Python package for postprocessing "
            "the simulation files is not found; then, test_5_transform.py is only run "
            "using resdata."
        )
    )

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_transform():
    """See examples/decks/MODEL0.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    readers = ["resdata"]
    if OPM:
        readers += ["opm"]
    for use in readers:
        flags = ["translate", "scale", "rotatexy", "rotatexz", "rotateyz"]
        values = ["[5,-3,2]", "[2,.5,4]", "45", "-10", "15"]
        checks = [3, 4, 1, 3.5899, 4.848]
        for flag, val, check in zip(flags, values, checks):
            sub = flag.upper() + use.upper()
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
                    "-warnings",
                    "1",
                    "-w",
                    sub,
                    "-l",
                    sub,
                    "-u",
                    use,
                ],
                check=True,
            )
            assert os.path.exists(f"{testpth}/output/transform/{sub}.INIT")
            assert os.path.exists(f"{testpth}/output/transform/{sub}.EGRID")
            grid = Grid(f"{testpth}/output/transform/{sub}.EGRID")
            zcoord = grid.export_corners(grid.export_index())[-1][-1]
            assert abs(zcoord - check) < 1e-2
