# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the ERT functionality via the TOML configuration file in Drogon."""

from pathlib import Path

import numpy as np
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid

from pycopm.core.pycopm import main
from .utils import assert_grid_and_init

DROGON_REGRESSION = {
    "dimensions": (23, 37, 16),
    "active": 8195,
    "checks": [
        ("PORV", np.sum, 548634176.0),
        ("DZ", np.min, 0.25049999356269836),
        ("DZ", np.max, 14.716500282287598),
        ("PERMX", np.min, 0.0010000000474974513),
        ("PERMX", np.max, 4303.46484375),
        ("TRANX", np.max, 369.0892333984375),
        ("TRANX", np.sum, 189191.0),
        ("TRANZ", np.sum, 335686464.0),
        ("TRANZ", np.max, 2366990.0),
        ("TRANNNC", np.sum, 7503.703125),
        ("TRANNNC", np.min, 1.4265186791817541e-06),
        ("TRANNNC", np.max, 104.9443359375),
    ],
    "exact": [
        ("SATNUM", np.sum, 63_389),
        ("FIPNUM", np.sum, 58_832),
    ],
    "data": {
        "length": 256,
    },
}


def test_1_ert(flow, tmp_path, monkeypatch):
    """See examples/configurations/drogon/input.toml."""

    repo_root = Path(__file__).parents[1]

    monkeypatch.chdir(tmp_path)

    config = repo_root / "examples" / "configurations" / "drogon" / "input.toml"

    main(["-i", str(config), "-o", "ert", "-f", flow])

    ert_dir = tmp_path / "ert"

    # Check generated files
    coeff_file = ert_dir / "parameters" / "coeff_lmltg_priors.data"
    content = coeff_file.read_text(encoding="utf8")

    assert content.count("lmltg") == 12

    parameters_file = ert_dir / "postprocessing" / "closest_to_obs" / "parameters.txt"

    lines = parameters_file.read_text(encoding="utf8").splitlines()

    assert len(lines) == 216

    assert (ert_dir / "postprocessing" / "hm_missmatch.png").is_file()

    deck = ert_dir / "postprocessing" / "closest_to_obs" / "DROGON_COARSER"

    assert_grid_and_init(
        OpmGrid(f"{deck}.EGRID"),
        OpmFile(f"{deck}.INIT"),
        dimensions=DROGON_REGRESSION["dimensions"],
        checks=DROGON_REGRESSION["checks"],
        exact_checks=DROGON_REGRESSION["exact"],
        active_cells=DROGON_REGRESSION["active"],
    )
