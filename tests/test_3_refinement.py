# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the generic refinement functionality"""

from pathlib import Path
import subprocess
import numpy as np
from opm.io.ecl import EclFile as OpmFile


def test_3_refinement(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL2.DATA"""
    monkeypatch.chdir(tmp_path)
    repo_root = Path(__file__).parents[1]
    sub = "FINER"
    subprocess.run(
        [
            "pycopm",
            "-i",
            f"{repo_root}/examples/decks/MODEL2.DATA",
            "-f",
            flow,
            "-g",
            "2,4,8",
            "-l",
            sub,
            "-w",
            sub,
            "-m",
            "all",
        ],
        check=True,
    )
    assert (tmp_path / f"{sub}.INIT").is_file()
    assert (tmp_path / f"{sub}.EGRID").is_file()
    porv = np.array(OpmFile(f"{sub}.INIT")["PORV"])
    assert abs(np.sum(porv) - 6506.25) < 1e-4
    assert np.sum(porv > 0) == 2430
