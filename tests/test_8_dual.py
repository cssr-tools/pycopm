# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the dual coarsening, i.e., splitting net and non-net cells"""

from pathlib import Path
import subprocess
import numpy as np
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import ERst as OpmRestart


def test_8_dual(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL6.DATA"""
    repo_root = Path(__file__).parents[1]
    monkeypatch.chdir(tmp_path)
    subprocess.run(
        [
            "pycopm",
            "-i",
            f"{repo_root}/examples/decks/MODEL6.DATA",
            "-f",
            flow,
            "-z",
            "1:4",
            "-w",
            "DUAL",
            "-dual",
            "poro <= 0.1",
            "D",
            "-t",
            "2",
            "-a",
            "max",
        ],
        check=True,
    )
    subprocess.run(
        [
            flow,
            "DUAL.DATA",
        ],
        check=True,
    )
    subprocess.run(
        [
            flow,
            f"{repo_root}/examples/decks/MODEL6.DATA",
            f"--output-dir={tmp_path}",
        ],
        check=True,
    )
    initr = OpmFile("MODEL6.INIT")
    initd = OpmFile("DUAL.INIT")
    assert (
        abs(np.sum(np.array(initr["PORV"])) - np.sum(np.array(initd["PORV"]))) < 1e-12
    ), "Issue with PORV and dual"
    assert (len(initd["PORV"])) == 24, "Issue with dimensions of the dual model"
    unrstr = OpmRestart("MODEL6.UNRST")
    unrstd = OpmRestart("DUAL.UNRST")
    assert (
        abs(unrstr["PRESSURE", 1][7,] - unrstd["PRESSURE", 1][7]) < 1e-1
    ), "Issue with the dual transsmissibility"
