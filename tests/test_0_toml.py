# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the configuration files for Norne."""

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid

from pycopm.core.pycopm import main

from .utils import assert_grid_and_init

RTOL = 1e-5
ATOL = 1e-8

REGRESSION = {
    "dimensions": (18, 44, 8),
    "active": 2262,
    "checks": [
        ("PORV", np.sum, 612132763.0322266),
        ("DZ", np.min, 1.0529999732971191),
        ("DZ", np.max, 106.9800033569336),
        ("PERMX", np.min, 4.3792619705200195),
        ("PERMX", np.max, 3996.548095703125),
        ("TRANX", np.max, 166012.03125),
        ("TRANX", np.sum, 565209.75),
        ("TRANZ", np.sum, 600854.6875),
        ("TRANZ", np.max, 19993.8203125),
        ("TRANNNC", np.sum, 1442.6361083984375),
        ("TRANNNC", np.min, 1.7060388017853256e-06),
        ("TRANNNC", np.max, 221.80421447753906),
    ],
    "exact": [
        ("SATNUM", np.sum, 2262),
        ("FIPNUM", np.sum, 14807),
    ],
    "data": {
        "length": 627,
    },
}

CPORV_CASES = [
    (1, 673148288.0),
]


def test_0_toml(flow, tmp_path, monkeypatch):
    """See examples/configurations/norne/input.toml."""

    monkeypatch.chdir(tmp_path)

    repo_root = Path(__file__).parents[1]

    input_config = repo_root / "examples" / "configurations" / "norne" / "input.toml"

    shutil.copy(input_config, "input.toml")

    main(["-f", flow])

    # Check generated output files
    assert (tmp_path / "postprocessing" / "errors.txt").is_file()

    assert (
        tmp_path / "postprocessing" / "wells" / "HISTO_DATA_WWPR_E-1H.png"
    ).is_file()

    deck = "output/simulations/realisation-0/iter-0/NORNE_ATW2013_COARSER"

    assert_grid_and_init(
        OpmGrid(f"{deck}.EGRID"),
        OpmFile(f"{deck}.INIT"),
        dimensions=REGRESSION["dimensions"],
        checks=REGRESSION["checks"],
        exact_checks=REGRESSION["exact"],
        active_cells=REGRESSION["active"],
    )

    # Check CPORV preprocessing
    for cporv, reference_pv in CPORV_CASES:
        config = f"cporv{cporv}.toml"

        shutil.copy(input_config, config)

        text = Path(config).read_text(encoding="utf-8")
        text = text.replace(
            "pore_volume_correction = 0",
            f"pore_volume_correction = {cporv}",
        )
        text = text.replace(
            '"single-run"',
            '"files"',
        )

        Path(config).write_text(text, encoding="utf-8")

        main(["-i", config, "-o", f"cporv{cporv}", "-f", flow, "-precision", "8"])

        deck = f"cporv{cporv}" "/preprocessing" "/NORNE_ATW2013_COARSER"

        subprocess.run(
            [flow, deck, "--enable-dry-run=1"],
            check=True,
        )

        tot_pv = np.sum(OpmFile(f"{deck}.INIT")["PORV"])

        assert tot_pv == pytest.approx(
            reference_pv,
            rel=RTOL,
            abs=ATOL,
        ), (
            f"sum(PORV) for cporv={cporv} = " f"{tot_pv}, expected {reference_pv}"
        )
