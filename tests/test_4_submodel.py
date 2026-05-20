# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the generic submodel functionality"""

from pathlib import Path
import subprocess
import numpy as np
from opm.io.ecl import EclFile as OpmFile


def test_4_submodel(flow, tmp_path, monkeypatch):
    """See examples/decks/MODEL0.DATA and MODEL1.DATA"""
    repo_root = Path(__file__).parents[1]
    monkeypatch.chdir(tmp_path)
    for i in range(2):
        sub = f"MODEL{i}_FINER"
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"{repo_root}/examples/decks/MODEL{i}.DATA",
                "-g",
                "4,4,3",
                "-w",
                sub,
                "-m",
                "all",
                "-l",
                sub,
                "-f",
                flow,
            ],
            check=True,
        )
        assert (tmp_path / f"{sub}.INIT").is_file()
        assert (tmp_path / f"{sub}.EGRID").is_file()
        for j in [1, 3, 4]:
            subprocess.run(
                [
                    "pycopm",
                    "-i",
                    f"{sub}.DATA",
                    "-f",
                    flow,
                    "-v",
                    "xypolygon [3,7.5] [7.5,3] [12,7.5] [7.5,12] [3,7.5]",
                    "-m",
                    "all",
                    "-w",
                    f"{sub}SUBMODEL",
                    "-l",
                    f"{sub}SUBMODEL",
                    "-p",
                    f"{j}",
                ],
                check=True,
            )
            porv = np.array(OpmFile(f"{sub}SUBMODEL.INIT")["PORV"])
            assert abs(np.sum(porv) - 150) < 1e-6
            assert np.sum(porv > 0) == 21
