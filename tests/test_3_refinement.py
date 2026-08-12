# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic refinement functionality."""

from pathlib import Path

import numpy as np
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid

from pycopm.core.pycopm import main

from .utils import assert_grid_and_init

REFINEMENT_CASES = [
    ("FINER", "-g", "2,4,8"),
    ("XREF", "-rx", "2,4,8"),
    ("YREF", "-ry", "5,8"),
    ("ZREF", "-rz", "3,2,1"),
]

REGRESSION_CASES = {
    "FINER": {
        "dimensions": (9, 10, 27),
        "active": 2430,
        "checks": [
            ("PORV", np.sum, 6506.25),
            ("PORV", np.min, 0.8333333134651184),
            ("PORV", np.max, 5.4166669845581055),
            ("DZ", np.sum, 3187.499755859375),
            ("DZ", np.min, 0.685182511806488),
            ("DZ", np.max, 2.203704357147217),
            ("TRANX", np.sum, 276.979248046875),
            ("TRANX", np.max, 0.33831751346588135),
            ("TRANY", np.sum, 253.1472625732422),
            ("TRANY", np.max, 0.31456199288368225),
            ("TRANZ", np.sum, 1833.096923828125),
            ("TRANZ", np.max, 2.508695363998413),
            ("TRANNNC", np.sum, 23.688396453857422),
            ("TRANNNC", np.min, 0.0009154602303169668),
            ("TRANNNC", np.max, 0.17431573569774628),
        ],
        "exact": [
            ("FIPNUM", np.sum, 4860),
        ],
        "data": {
            "length": 127,
            "faults": [
                (1, 1, 1, 1, 1, 9),
                (1, 1, 2, 2, 1, 9),
            ],
            "welspecs": (2, 3),
            "compdat": ("INJ00", 2, 3, 1),
        },
    },
    "XREF": {
        "dimensions": (17, 2, 3),
        "active": 102,
        "checks": [
            ("PORV", np.sum, 6506.25048828125),
            ("PORV", np.min, 12.5),
            ("PORV", np.max, 243.75),
            ("DZ", np.sum, 1197.5),
            ("DZ", np.min, 7.5),
            ("DZ", np.max, 19.44444465637207),
            ("TRANX", np.sum, 1301.899658203125),
            ("TRANX", np.max, 37.898685455322266),
            ("TRANY", np.sum, 4.522024154663086),
            ("TRANY", np.max, 0.3784891366958618),
            ("TRANZ", np.sum, 14.968362808227539),
            ("TRANZ", np.max, 0.737098217010498),
        ],
        "exact": [
            ("FIPNUM", np.sum, 204),
        ],
        "data": {
            "length": 123,
            "faults": [
                (1, 1, 1, 1, 1, 1),
                (1, 1, 1, 1, 1, 1),
                (2, 2, 1, 1, 1, 1),
                (3, 3, 1, 1, 1, 1),
            ],
            "welspecs": (2, 1),
            "compdat": ("INJ00", 2, 1, 1),
        },
    },
    "YREF": {
        "dimensions": (3, 15, 3),
        "active": 135,
        "checks": [
            ("PORV", np.sum, 6506.25),
            ("PORV", np.min, 18.75),
            ("PORV", np.max, 81.25),
            ("DZ", np.sum, 1612.5),
            ("DZ", np.min, 7.5),
            ("DZ", np.max, 19.58333396911621),
            ("TRANX", np.sum, 22.90654945373535),
            ("TRANX", np.max, 0.4678855240345001),
            ("TRANY", np.sum, 563.0792846679688),
            ("TRANY", np.max, 9.349223136901855),
            ("TRANZ", np.sum, 14.644294738769531),
            ("TRANZ", np.max, 0.30617889761924744),
        ],
        "exact": [
            ("FIPNUM", np.sum, 270),
        ],
        "data": {
            "length": 126,
            "faults": [
                (1, 1, 1, 1, 1, 1),
                (1, 1, 2, 2, 1, 1),
            ],
            "welspecs": (1, 3),
            "compdat": ("INJ00", 1, 3, 1),
        },
    },
    "ZREF": {
        "dimensions": (3, 2, 9),
        "active": 54,
        "checks": [
            ("PORV", np.sum, 6506.25),
            ("PORV", np.min, 37.5),
            ("PORV", np.max, 337.5),
            ("DZ", np.sum, 212.5),
            ("DZ", np.min, 2.5),
            ("DZ", np.max, 5.0),
            ("TRANX", np.sum, 20.653560638427734),
            ("TRANX", np.max, 2.0514936447143555),
            ("TRANY", np.sum, 4.10537052154541),
            ("TRANY", np.max, 0.22486722469329834),
            ("TRANZ", np.sum, 163.322021484375),
            ("TRANZ", np.max, 6.219264984130859),
            ("TRANNNC", np.sum, 2.8992433547973633),
            ("TRANNNC", np.min, 0.016318587586283684),
            ("TRANNNC", np.max, 0.215155690908432),
        ],
        "exact": [
            ("FIPNUM", np.sum, 96),
        ],
        "data": {
            "length": 121,
            "faults": [
                (1, 1, 1, 1, 1, 4),
                (1, 1, 1, 1, 1, 4),
            ],
            "welspecs": (1, 1),
            "compdat": ("INJ00", 1, 1, 1),
        },
    },
}


def test_3_refinement(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL2.DATA."""

    monkeypatch.chdir(tmp_path)

    repo_root = Path(__file__).parents[1]
    model = repo_root / "examples" / "decks" / "MODEL2.DATA"

    for deck, option, value in REFINEMENT_CASES:
        main(
            [
                "-i",
                str(model),
                "-f",
                flow,
                option,
                value,
                "-w",
                deck,
                "-m",
                "all",
            ]
        )

        assert (tmp_path / f"{deck}.INIT").is_file()
        assert (tmp_path / f"{deck}.EGRID").is_file()

    for deck, reference in REGRESSION_CASES.items():
        assert_grid_and_init(
            OpmGrid(f"{deck}.EGRID"),
            OpmFile(f"{deck}.INIT"),
            dimensions=reference["dimensions"],
            checks=reference["checks"],
            exact_checks=reference["exact"],
            active_cells=reference["active"],
        )
