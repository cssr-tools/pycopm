# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0913,R0917

"""Test the dual coarsening, i.e., splitting net and non-net cells"""

from pathlib import Path
import subprocess
import pytest
import numpy as np
from opm.io.ecl import EclFile as OpmFile

TOL = {"rtol": 1e-5, "atol": 1e-8}


@pytest.mark.parametrize(
    "deck,z_range,dual_expr,expected",
    [
        (
            "MODEL6.DATA",
            "1:4",
            "poro <= 0.1, vertical TF = 0",
            {
                "PORV": np.array(
                    [
                        6.25e8,
                        1.25e9,
                        6.25e8,
                        6.25e8,
                        6.25e8,
                        6.25e8,
                        1.25e9,
                        6.25e8,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        2.50e8,
                        2.50e8,
                        2.50e8,
                        2.50e8,
                        0,
                        0,
                    ]
                ),
                "TRANX": np.array(
                    [
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        0,
                        3.410807e-2,
                        3.410807e-2,
                        3.410807e-2,
                        0,
                    ]
                ),
                "TRANY": np.zeros(12),
                "TRANNNC": np.array([0.0682094, 0.0682094]),
                "NNC1": np.array([2, 7]),
                "NNC2": np.array([19, 22]),
            },
        ),
        (
            "MODEL6.DATA",
            "1:4",
            "poro <= 0.1",
            {
                "PORV": np.array(
                    [
                        6.25e8,
                        1.25e9,
                        6.25e8,
                        6.25e8,
                        6.25e8,
                        6.25e8,
                        1.25e9,
                        6.25e8,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        2.50e8,
                        2.50e8,
                        2.50e8,
                        2.50e8,
                        0,
                        0,
                    ]
                ),
                "TRANX": np.array(
                    [
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        3.456000e2,
                        0,
                        3.410807e-2,
                        3.410807e-2,
                        3.410807e-2,
                        0,
                    ]
                ),
                "TRANY": np.zeros(12),
                "TRANNNC": np.array(
                    [0.0682094, 2.5578527, 2.5578527, 2.5578527, 2.5578527, 0.0682094]
                ),
                "NNC1": np.array([2, 3, 4, 5, 6, 7]),
                "NNC2": np.array([19, 19, 20, 21, 22, 22]),
            },
        ),
        (
            "MODEL7.DATA",
            "1:2",
            "poro == 0.1",
            {
                "PORV": np.array(
                    [
                        250000,
                        500000,
                        250000,
                        250000,
                        0,
                        250000,
                        250000,
                        500000,
                        250000,
                        0,
                        0,
                        0,
                        100000,
                        0,
                        100000,
                        100000,
                        200000,
                        100000,
                        100000,
                        0,
                        100000,
                    ]
                ),
                "TRANX": np.array(
                    [
                        4.000002e0,
                        1.000002e0,
                        0,
                        0,
                        0,
                        1.000002e0,
                        1.000002e0,
                        0,
                        0,
                        0,
                        1.000002e-2,
                        1.101000e1,
                        0,
                        0,
                        0,
                    ]
                ),
                "TRANY": np.array(
                    [
                        1.000002,
                        0,
                        1.000002,
                        1.000002,
                        1.000002,
                        0,
                        0,
                        0,
                        0.01000002,
                        0.01000002,
                        0.01000002,
                        0,
                        0.01000002,
                        0,
                        0,
                    ]
                ),
                "TRANNNC": np.array(
                    [
                        0.01980202,
                        7,
                        0.01980202,
                        0.01980202,
                        0.03960404,
                        0.01980202,
                        0.01980202,
                        0.01980202,
                        0.01980202,
                        0.01980202,
                        0.01980202,
                        0.03960404,
                        0.01980202,
                        0.01980202,
                        0.01980202,
                    ]
                ),
                "NNC1": np.array([1, 1, 2, 2, 2, 3, 4, 4, 6, 6, 7, 8, 8, 8, 9]),
                "NNC2": np.array(
                    [13, 16, 13, 15, 17, 15, 16, 17, 17, 18, 19, 17, 19, 21, 21]
                ),
            },
        ),
        (
            "MODEL8.DATA",
            "1:2",
            "poro == 0.1",
            {
                "PORV": np.array(
                    [
                        6.2500e8,
                        1.5625e8,
                        4.6875e8,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        1.8750e8,
                        1.8750e8,
                        0,
                        3.1250e8,
                        0,
                    ]
                ),
                "TRANX": np.array([1.000002, 1.000002, 0, 0.01000002, 0, 0.0]),
                "TRANY": np.array([0, 0, 0, 0.18750042, 0, 0.0]),
                "TRANNNC": np.array(
                    [0.01980202, 0.66445315, 0.12376262, 0.03960404, 0.6600673]
                ),
                "NNC1": np.array([1, 2, 2, 3, 3]),
                "NNC2": np.array([11, 11, 14, 11, 12]),
            },
        ),
    ],
)
def test_8_dual(flow, tmp_path, monkeypatch, deck, z_range, dual_expr, expected):
    """See examples/decks/MODEL7.DATA and MODEL.DATA"""
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    cmd = [
        "pycopm",
        "-i",
        str(repo_root / f"examples/decks/{deck}"),
        "-f",
        flow,
        "-z",
        z_range,
        "-w",
        "DUAL",
        "-dual",
        dual_expr,
        "D",
        "-t",
        "2",
        "-m",
        "all",
        "-a",
        "max",
    ]

    subprocess.run(cmd, check=True)

    init = OpmFile("DUAL.INIT")
    egrid = OpmFile("DUAL.EGRID")

    np.testing.assert_allclose(
        init["PORV"], expected["PORV"], err_msg="PORV mismatch", **TOL
    )
    np.testing.assert_allclose(
        init["TRANX"], expected["TRANX"], err_msg="TRANX mismatch", **TOL
    )
    np.testing.assert_allclose(
        init["TRANY"], expected["TRANY"], err_msg="TRANY mismatch", **TOL
    )
    np.testing.assert_allclose(
        init["TRANNNC"], expected["TRANNNC"], err_msg="TRANNNC mismatch", **TOL
    )

    np.testing.assert_array_equal(
        egrid["NNC1"], expected["NNC1"], err_msg="NNC1 mismatch"
    )
    np.testing.assert_array_equal(
        egrid["NNC2"], expected["NNC2"], err_msg="NNC2 mismatch"
    )
