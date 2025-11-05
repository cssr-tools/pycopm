# SPDX-FileCopyrightText: 2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic affine transformation functionality"""

import os
import pathlib
import subprocess
from opm.io.ecl import EGrid as OpmGrid

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_transform(flow):
    """See examples/decks/MODEL0.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    flags = ["translate", "scale", "rotatexy", "rotatexz", "rotateyz"]
    values = ["[5,-3,2]", "[2,.5,4]", "45", "-10", "15"]
    checks = [3, 4, 1, 3.5899, 4.848]
    for flag, val, check in zip(flags, values, checks):
        sub = flag.upper()
        subprocess.run(
            [
                "pycopm",
                "-f",
                flow,
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
            ],
            check=True,
        )
        assert os.path.exists(f"{testpth}/output/transform/{sub}.INIT")
        assert os.path.exists(f"{testpth}/output/transform/{sub}.EGRID")
        grid = OpmGrid(f"{testpth}/output/transform/{sub}.EGRID")
        dim = grid.dimension
        zcoord = grid.xyz_from_ijk(dim[0] - 1, dim[1] - 1, dim[2] - 1)[-1][-1]
        assert abs(zcoord - check) < 1e-2
