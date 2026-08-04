# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the generic affine transformation functionality."""

from pathlib import Path

import pytest
from opm.io.ecl import EGrid as OpmGrid

from pycopm.core.pycopm import main

ABS_TOL = 1e-2

TRANSFORM_CASES = [
    ("translate", "[5,-3,2]", 3.0),
    ("scale", "[2,.5,4]", 4.0),
    ("rotatexy", "45", 1.0),
    ("rotatexz", "-10", 3.5899),
    ("rotateyz", "15", 4.8480),
]


def test_5_transform(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL0.DATA."""

    repo_root = Path(__file__).parents[1]
    model = repo_root / "examples" / "decks" / "MODEL0.DATA"

    monkeypatch.chdir(tmp_path)

    for transform, value, expected_z in TRANSFORM_CASES:
        name = transform.upper()

        main(
            [
                "-i",
                str(model),
                "-f",
                flow,
                "-d",
                f"{transform} {value}",
                "-m",
                "all",
                "-w",
                name,
                "-l",
                name,
            ]
        )

        assert (tmp_path / f"{name}.INIT").is_file()
        assert (tmp_path / f"{name}.EGRID").is_file()

        grid = OpmGrid(f"{name}.EGRID")

        nx, ny, nz = grid.dimension

        zcoord = grid.xyz_from_ijk(
            nx - 1,
            ny - 1,
            nz - 1,
        )[
            -1
        ][-1]

        assert zcoord == pytest.approx(
            expected_z,
            abs=ABS_TOL,
        ), (
            f"{transform}: z-coordinate = {zcoord}, " f"expected {expected_z}"
        )
