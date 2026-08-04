# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the generic coarsening functionality."""

from pathlib import Path

import numpy as np
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid

from pycopm.core.pycopm import main
from .utils import assert_grid_and_init

REGRESSION_CASES = {
    "FINER": {
        "dimensions": (16, 11, 1),
        "active": 164,
        "checks": [
            ("PORV", np.sum, 35.57999801635742),
            ("TRANX", np.sum, 2317.359130859375),
            ("TRANY", np.sum, 1189.00341796875),
            ("PERMX", np.sum, 173650.0),
        ],
        "exact": [
            ("SATNUM", np.sum, 164),
            ("FIPNUM", np.sum, 1646),
        ],
    },
    "TRANSFINER": {
        "dimensions": (20, 4, 1),
        "active": 70,
        "checks": [
            ("PORV", np.sum, 35.500003814697266),
            ("TRANX", np.sum, 3005.7734375),
            ("TRANY", np.sum, 310.00250244140625),
        ],
        "exact": [
            ("SATNUM", np.sum, 70),
            ("FIPNUM", np.sum, 570),
        ],
    },
    "TRANS2FINER": {
        "dimensions": (4, 20, 1),
        "active": 70,
        "checks": [
            ("PORV", np.sum, 35.5),
            ("TRANX", np.sum, 413.5602722167969),
            ("TRANY", np.sum, 2984.8701171875),
        ],
        "exact": [
            ("SATNUM", np.sum, 70),
            ("FIPNUM", np.sum, 710),
        ],
    },
    "MAXMAXMAX": {
        "dimensions": (4, 4, 1),
        "active": 15,
        "checks": [
            ("PORV", np.sum, 35.58000183105469),
            ("PERMX", np.sum, 19300.0),
            ("TRANX", np.sum, 121.81452178955078),
            ("TRANY", np.sum, 114.68026733398438),
        ],
        "exact": [
            ("SATNUM", np.sum, 15),
            ("FIPNUM", np.sum, 178),
        ],
    },
    "MAXMAXPVMEAN": {
        "dimensions": (4, 4, 1),
        "active": 15,
        "checks": [
            ("PORV", np.sum, 35.58000183105469),
            ("PERMX", np.sum, 16063.4599609375),
            ("TRANX", np.sum, 102.1654281616211),
            ("TRANY", np.sum, 94.2510986328125),
        ],
        "exact": [
            ("SATNUM", np.sum, 15),
            ("FIPNUM", np.sum, 178),
        ],
    },
    "MAXMINMIN": {
        "dimensions": (4, 4, 1),
        "active": 15,
        "checks": [
            ("PORV", np.sum, 35.58000183105469),
            ("PERMX", np.sum, 13700.0),
            ("TRANX", np.sum, 87.6861572265625),
            ("TRANY", np.sum, 76.83136749267578),
        ],
        "exact": [
            ("SATNUM", np.sum, 15),
            ("FIPNUM", np.sum, 122),
        ],
    },
    "MINMAXMAX": {
        "dimensions": (4, 4, 1),
        "active": 14,
        "checks": [
            ("PORV", np.sum, 35.5),
            ("PERMX", np.sum, 18000.0),
            ("TRANX", np.sum, 98.06068420410156),
            ("TRANY", np.sum, 91.60452270507812),
        ],
        "exact": [
            ("SATNUM", np.sum, 14),
            ("FIPNUM", np.sum, 170),
        ],
    },
    "MODEMAXPVMEAN": {
        "dimensions": (4, 4, 1),
        "active": 14,
        "checks": [
            ("PORV", np.sum, 35.5),
            ("PERMX", np.sum, 14763.4599609375),
            ("TRANX", np.sum, 80.21043395996094),
            ("TRANY", np.sum, 73.23786926269531),
        ],
        "exact": [
            ("SATNUM", np.sum, 14),
            ("FIPNUM", np.sum, 170),
        ],
    },
    "MINMINMIN": {
        "dimensions": (4, 4, 1),
        "active": 14,
        "checks": [
            ("PORV", np.sum, 35.5),
            ("PERMX", np.sum, 12400.0),
            ("TRANX", np.sum, 67.36343383789062),
            ("TRANY", np.sum, 57.598365783691406),
        ],
        "exact": [
            ("SATNUM", np.sum, 14),
            ("FIPNUM", np.sum, 114),
        ],
    },
}


def test_2_coarsening(flow, tmp_path, monkeypatch):
    """See examples/decks/HELLO_WORLD.DATA."""

    repo_root = Path(__file__).parents[1]
    model = repo_root / "examples" / "decks" / "HELLO_WORLD.DATA"

    monkeypatch.chdir(tmp_path)

    main(
        [
            "-f",
            flow,
            "-c",
            "5,5,1",
            "-i",
            str(model),
            "-m",
            "prep",
        ]
    )

    assert (tmp_path / "HELLO_WORLD_PREP_PYCOPM_DRYRUN.INIT").is_file()
    assert (tmp_path / "HELLO_WORLD_PREP_PYCOPM_DRYRUN.EGRID").is_file()

    for ahow in ("max", "min", "mode"):
        for nhow in ("max", "min", "mode"):
            for show in ("max", "min", "mean", "pvmean"):
                deck = f"{ahow}{nhow}{show}"

                main(
                    [
                        "-f",
                        flow,
                        "-i",
                        str(model),
                        "-c",
                        "5,5,1",
                        "-m",
                        "all",
                        "-a",
                        ahow,
                        "-n",
                        nhow,
                        "-s",
                        show,
                        "-w",
                        deck.upper(),
                    ]
                )

                assert (tmp_path / f"{deck.upper()}.INIT").is_file()
                assert (tmp_path / f"{deck.upper()}.EGRID").is_file()

    main(
        [
            "-f",
            flow,
            "-i",
            str(model),
            "-m",
            "deck_dry",
            "-p",
            "1",
            "-n",
            "mode",
            "-x",
            "6:10",
            "-y",
            "0,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,2,2,0,0,0",
            "-w",
            "FINER",
        ]
    )

    assert (tmp_path / "FINER.INIT").is_file()
    assert (tmp_path / "FINER.EGRID").is_file()

    main(
        [
            "-f",
            flow,
            "-i",
            str(model),
            "-c",
            "1,5,1",
            "-m",
            "deck_dry",
            "-t",
            "1",
            "-w",
            "TRANSFINER",
        ]
    )

    assert (tmp_path / "TRANSFINER.INIT").is_file()
    assert (tmp_path / "TRANSFINER.EGRID").is_file()

    main(
        [
            "-f",
            flow,
            "-i",
            str(model),
            "-c",
            "5,1,4",
            "-m",
            "deck_dry",
            "-t",
            "2",
            "-w",
            "TRANS2FINER",
        ]
    )

    assert (tmp_path / "TRANS2FINER.INIT").is_file()
    assert (tmp_path / "TRANS2FINER.EGRID").is_file()

    for deck, reference in REGRESSION_CASES.items():
        assert_grid_and_init(
            OpmGrid(f"{deck}.EGRID"),
            OpmFile(f"{deck}.INIT"),
            dimensions=reference["dimensions"],
            checks=reference["checks"],
            exact_checks=reference["exact"],
            active_cells=reference["active"],
        )
