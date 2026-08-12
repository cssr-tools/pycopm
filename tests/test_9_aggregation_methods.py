# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0913,R0917

"""Test active, discrete, and continuous z-coarsening methods."""

from pathlib import Path

import numpy as np
import pytest
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid

from pycopm.core.pycopm import main

from .utils import assert_grid_and_init

RTOL = 1e-5
ATOL = 1e-8

ACTIVE_CASES = [
    ("min", 1),
    ("max", 2),
    ("mode", 2),
]

DISCRETE_CASES = [
    ("min", 1),
    ("max", 2),
    ("mode", 2),
]

CONTINUOUS_CASES = [
    ("min", 100.0),
    ("max", 400.0),
    ("mean", 700.0 / 3.0),
    ("pvmean", 170.0 / 0.6),
]

REGRESSION_CASES = {
    "RANGE_METHODS": {
        "dimensions": (1, 1, 4),
        "active": 4,
        "checks": [
            ("PERMX", np.sum, 100.0 + 100.0 + 700.0 / 3.0 + 530.0),
        ],
        "exact": [
            ("FIPNUM", np.sum, 6),
        ],
    },
}


def run_coarsening(flow, model, output, *options):
    """Run one complete z-coarsening case."""

    main(
        [
            "-m",
            "all",
            "-f",
            flow,
            "-i",
            str(model),
            "-precision",
            "0",
            "-w",
            output,
            *options,
        ]
    )


@pytest.mark.parametrize("method,active", ACTIVE_CASES)
def test_aggregation_active_cells(flow, tmp_path, monkeypatch, method, active):
    """Test min, max, and mode aggregation of ACTNUM."""

    repo_root = Path(__file__).parents[1]
    model = repo_root / "examples" / "decks" / "AGGREGATION4.DATA"
    output = f"ACTIVE_{method.upper()}"

    monkeypatch.chdir(tmp_path)

    run_coarsening(
        flow,
        model,
        output,
        "-z",
        "1:1,2:4",
        "-a",
        method,
    )

    assert (tmp_path / f"{output}.INIT").is_file()
    assert (tmp_path / f"{output}.EGRID").is_file()

    grid = OpmGrid(f"{output}.EGRID")
    init = OpmFile(f"{output}.INIT")

    assert_grid_and_init(
        grid,
        init,
        dimensions=(1, 1, 2),
        checks=[],
        exact_checks=[],
        active_cells=active,
    )


@pytest.mark.parametrize("nhow,expected", DISCRETE_CASES)
def test_aggregation_discrete_values(flow, tmp_path, monkeypatch, nhow, expected):
    """Test min, max, and mode aggregation of discrete properties."""

    repo_root = Path(__file__).parents[1]
    model = repo_root / "examples" / "decks" / "AGGREGATION4.DATA"
    output = f"DISCRETE_{nhow.upper()}"

    monkeypatch.chdir(tmp_path)

    run_coarsening(
        flow,
        model,
        output,
        "-z",
        "1:4",
        "-a",
        "max",
        "-n",
        nhow,
    )

    init = OpmFile(f"{output}.INIT")

    np.testing.assert_array_equal(init["FIPNUM"], np.array([expected]))


@pytest.mark.parametrize("show,expected", CONTINUOUS_CASES)
def test_aggregation_continuous_values(flow, tmp_path, monkeypatch, show, expected):
    """Test min, max, mean, and pore-volume-weighted aggregation."""

    repo_root = Path(__file__).parents[1]
    model = repo_root / "examples" / "decks" / "AGGREGATION4.DATA"
    output = f"CONTINUOUS_{show.upper()}"

    monkeypatch.chdir(tmp_path)

    run_coarsening(
        flow,
        model,
        output,
        "-z",
        "1:4",
        "-a",
        "max",
        "-s",
        show,
    )

    init = OpmFile(f"{output}.INIT")

    np.testing.assert_allclose(
        init["PERMX"],
        np.array([expected]),
        rtol=RTOL,
        atol=ATOL,
    )


def test_aggregation_methods_per_z_range(flow, tmp_path, monkeypatch):
    """Test simultaneous per-range values for -a, -n, and -s."""

    repo_root = Path(__file__).parents[1]
    model = repo_root / "examples" / "decks" / "AGGREGATION16.DATA"
    output = "RANGE_METHODS"

    monkeypatch.chdir(tmp_path)

    run_coarsening(
        flow,
        model,
        output,
        "-z",
        "1:4,5:8,9:12,13:16",
        "-a",
        "min,max,mode,mode",
        "-n",
        "min,max,mode,mode",
        "-s",
        "min,max,mean,pvmean",
    )

    assert (tmp_path / f"{output}.INIT").is_file()
    assert (tmp_path / f"{output}.EGRID").is_file()

    grid = OpmGrid(f"{output}.EGRID")
    init = OpmFile(f"{output}.INIT")
    reference = REGRESSION_CASES[output]

    assert_grid_and_init(
        grid,
        init,
        dimensions=reference["dimensions"],
        checks=reference["checks"],
        exact_checks=reference["exact"],
        active_cells=reference["active"],
    )

    np.testing.assert_allclose(
        init["PERMX"],
        np.array([100.0, 100.0, 700.0 / 3.0, 530.0]),
        rtol=RTOL,
        atol=ATOL,
    )
    np.testing.assert_array_equal(
        init["FIPNUM"],
        np.array([1, 1, 2, 2]),
    )
