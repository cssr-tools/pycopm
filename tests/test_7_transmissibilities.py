# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0914

"""Test the coarsening by transmissibilities"""

from pathlib import Path
import subprocess
import numpy as np
from opm.io.ecl import EclFile as OpmFile


def test_7_transmissibilities(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL4.DATA and MODEL5.DATA"""
    repo_root = Path(__file__).parents[1]
    monkeypatch.chdir(tmp_path)
    values = [
        [696.14886, 774.826, 5008.1323, 13739.814453],
        [696.14886, 774.826, 0, 13739.814453],
    ]
    for i, sub in enumerate(["1", "2"]):
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"{repo_root}/examples/decks/MODEL4.DATA",
                "-z",
                "1:30,31:56,57:111,112:116,117:217",
                "-w",
                f"COARSER{sub}",
                "-f",
                flow,
                "-a",
                "max",
                "-l",
                f"C0{sub}",
                "-t",
                sub,
                "-m",
                "all",
            ],
            check=True,
        )
        init = OpmFile(f"COARSER{sub}.INIT")
        for j, n in enumerate(["X", "Y", "Z", "NNC"]):
            assert (
                abs(np.sum(np.array(init[f"TRAN{n}"])) - values[i][j]) < 1e-5
            ), f"Issue in TRAN{n} with -t {i}"
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"{repo_root}/examples/decks/MODEL5.DATA",
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
            ],
            check=True,
        )
        init_ref = OpmFile("MODEL5_PREP_PYCOPM_DRYRUN.INIT")
        init = OpmFile("COARSER_MODEL5.INIT")
        assert (
            abs(init["TRANX"][0] - 2 * init_ref["TRANX"][0]) < 1e-5
        ), "Issue in TRANX with MODEL5 (NNCTRAN[0])"
        assert (
            abs(init["TRANX"][-2] - 2 * init_ref["TRANX"][0]) < 1e-5
        ), "Issue in TRANX with MODEL5 (NNCTRAN[-2])"
