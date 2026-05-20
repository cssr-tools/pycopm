# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the generic affine transformation functionality"""

from pathlib import Path
import subprocess
from opm.io.ecl import EGrid as OpmGrid


def test_5_transform(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL0.DATA"""
    repo_root = Path(__file__).parents[1]
    monkeypatch.chdir(tmp_path)
    flags = ["translate", "scale", "rotatexy", "rotatexz", "rotateyz"]
    values = ["[5,-3,2]", "[2,.5,4]", "45", "-10", "15"]
    checks = [3, 4, 1, 3.5899, 4.848]
    for flag, val, check in zip(flags, values, checks):
        sub = flag.upper()
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"{repo_root}/examples/decks/MODEL0.DATA",
                "-f",
                flow,
                "-d",
                f"{flag} {val}",
                "-m",
                "all",
                "-w",
                sub,
                "-l",
                sub,
            ],
            check=True,
        )
        assert (tmp_path / f"{sub}.INIT").is_file()
        assert (tmp_path / f"{sub}.EGRID").is_file()
        grid = OpmGrid(f"{sub}.EGRID")
        dim = grid.dimension
        zcoord = grid.xyz_from_ijk(dim[0] - 1, dim[1] - 1, dim[2] - 1)[-1][-1]
        assert abs(zcoord - check) < 1e-2
