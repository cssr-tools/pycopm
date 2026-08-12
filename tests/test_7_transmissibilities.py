# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0914,R0801

"""Test the coarsening by transmissibilities."""

from pathlib import Path

import numpy as np
import pytest
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid

from pycopm.core.pycopm import main

from .utils import assert_grid_and_init

RTOL = 1e-5
ATOL = 1e-8

REGRESSION_CASES = {
    "COARSER1": {
        "dimensions": (3, 3, 5),
        "active": 43,
        "checks": [
            ("PORV", np.sum, 96214656.0),
            ("PORV", np.min, 0.0),
            ("PORV", np.max, 5929101.0),
            ("DZ", np.sum, 2747.1123046875),
            ("DZ", np.min, 10.770000457763672),
            ("DZ", np.max, 145.52499389648438),
            ("PERMX", np.sum, 96.75543212890625),
            ("PERMX", np.max, 96.75543212890625),
            ("TRANX", np.sum, 827.3911743164062),
            ("TRANX", np.max, 96.01197052001953),
            ("TRANY", np.sum, 968.17822265625),
            ("TRANY", np.max, 93.61161804199219),
            ("TRANZ", np.sum, 5008.13232421875),
            ("TRANZ", np.max, 933.578125),
            ("TRANNNC", np.sum, 13739.814453125),
            ("TRANNNC", np.min, 0.4228149354457855),
            ("TRANNNC", np.max, 25.62749671936035),
        ],
        "exact": [
            ("FIPNUM", np.sum, 157),
        ],
        "data": {
            "length": 84,
            "welspecs": (2, 2),
            "compdat": ("INJ00", 2, 2, 1),
        },
    },
    "COARSER2": {
        "dimensions": (3, 3, 5),
        "active": 43,
        "checks": [
            ("PORV", np.sum, 96214656.0),
            ("PORV", np.min, 0.0),
            ("PORV", np.max, 5929101.0),
            ("DZ", np.sum, 2747.1123046875),
            ("DZ", np.min, 10.770000457763672),
            ("DZ", np.max, 145.52499389648438),
            ("PERMX", np.sum, 96.75543212890625),
            ("PERMX", np.max, 96.75543212890625),
            ("TRANX", np.sum, 827.3911743164062),
            ("TRANX", np.max, 96.01197052001953),
            ("TRANY", np.sum, 968.17822265625),
            ("TRANY", np.max, 93.61161804199219),
            ("TRANZ", np.sum, 8564.0341796875),
            ("TRANZ", np.max, 4563.7099609375),
            ("TRANNNC", np.sum, 13739.814453125),
            ("TRANNNC", np.min, 0.4228149354457855),
            ("TRANNNC", np.max, 25.62749671936035),
        ],
        "exact": [
            ("FIPNUM", np.sum, 157),
        ],
        "data": {
            "length": 84,
            "welspecs": (2, 2),
            "compdat": ("INJ00", 2, 2, 1),
        },
    },
    "COARSER_MODEL5": {
        "dimensions": (4, 1, 1),
        "active": 4,
        "checks": [
            ("PORV", np.sum, 10000000000.0),
            ("PORV", np.min, 2500000000.0),
            ("PORV", np.max, 2500000000.0),
            ("DZ", np.sum, 4000.0),
            ("DZ", np.min, 1000.0),
            ("DZ", np.max, 1000.0),
            ("TRANX", np.sum, 103.65443420410156),
            ("TRANX", np.max, 34.55147933959961),
        ],
        "exact": [
            ("SATNUM", np.sum, 4),
            ("FIPNUM", np.sum, 4),
        ],
        "data": {
            "length": 95,
            "source": [
                (4, 1, 1),
            ],
        },
    },
}


def test_7_transmissibilities(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL4.DATA and MODEL5.DATA."""

    repo_root = Path(__file__).parents[1]

    monkeypatch.chdir(tmp_path)

    model4 = repo_root / "examples" / "decks" / "MODEL4.DATA"
    model5 = repo_root / "examples" / "decks" / "MODEL5.DATA"

    for trans_mode in ("1", "2"):
        main(
            [
                "-i",
                str(model4),
                "-z",
                "1:30,31:56,57:111,112:116,117:217",
                "-w",
                f"COARSER{trans_mode}",
                "-f",
                flow,
                "-a",
                "max",
                "-l",
                f"C0{trans_mode}",
                "-t",
                trans_mode,
                "-m",
                "all",
            ]
        )

        assert (tmp_path / f"COARSER{trans_mode}.INIT").is_file()

    main(
        [
            "-i",
            str(model5),
            "-z",
            "1:2",
            "-w",
            "COARSER_MODEL5",
            "-l",
            "CM5",
            "-t",
            "2",
            "-a",
            "max",
            "-f",
            flow,
            "-m",
            "all",
        ]
    )

    init_ref = OpmFile("MODEL5_PREP_PYCOPM_DRYRUN.INIT")
    init = OpmFile("COARSER_MODEL5.INIT")

    reference = 2 * init_ref["TRANX"][0]

    assert init["TRANX"][0] == pytest.approx(
        reference,
        rel=RTOL,
        abs=ATOL,
    ), "Issue in TRANX with MODEL5 (TRANX[0])"

    assert init["TRANX"][-2] == pytest.approx(
        reference,
        rel=RTOL,
        abs=ATOL,
    ), "Issue in TRANX with MODEL5 (TRANX[-2])"

    for deck, reference in REGRESSION_CASES.items():
        assert_grid_and_init(
            OpmGrid(f"{deck}.EGRID"),
            OpmFile(f"{deck}.INIT"),
            dimensions=reference["dimensions"],
            checks=reference["checks"],
            exact_checks=reference["exact"],
            active_cells=reference["active"],
            data_file=f"{deck}.DATA",
            data_checks=reference.get("data"),
        )
