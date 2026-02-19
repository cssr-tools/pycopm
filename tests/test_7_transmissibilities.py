# SPDX-FileCopyrightText: 2025-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801,R0914

"""Test the coarsening by transmissibilities"""

import os
import pathlib
import subprocess
import numpy as np
from opm.io.ecl import EclFile as OpmFile

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_transmissibilities(flow):
    """See examples/decks/MODEL4.DATA and MODEL5.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    values = [
        [696.14886, 774.826, 5008.1323, 106.21955],
        [696.14886, 774.826, 0, 106.21955],
    ]
    for i, sub in enumerate(["1", "2"]):
        subprocess.run(
            [
                "pycopm",
                "-f",
                flow,
                "-o",
                f"{testpth}/output/transmissibilities",
                "-i",
                f"{mainpth}/examples/decks/MODEL4.DATA",
                "-z",
                "1:30,31:56,57:111,112:116,117:217",
                "-w",
                f"COARSER{sub}",
                "-l",
                f"C0{sub}",
                "-t",
                sub,
                "-a",
                "max",
                "-m",
                "all",
            ],
            check=True,
        )
        init = OpmFile(f"{testpth}/output/transmissibilities/COARSER{sub}.INIT")
        for j, n in enumerate(["X", "Y", "Z", "NNC"]):
            assert (
                abs(np.sum(np.array(init[f"TRAN{n}"])) - values[i][j]) < 1e-5
            ), f"Issue in TRAN{n} with -t {i}"
        subprocess.run(
            [
                "pycopm",
                "-f",
                flow,
                "-o",
                f"{testpth}/output/transmissibilities",
                "-i",
                f"{mainpth}/examples/decks/MODEL5.DATA",
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
                "-m",
                "all",
            ],
            check=True,
        )
        ref = "MODEL5_PREP_PYCOPM_DRYRUN.INIT"
        init_ref = OpmFile(f"{testpth}/output/transmissibilities/{ref}")
        init = OpmFile(f"{testpth}/output/transmissibilities/COARSER_MODEL5.INIT")
        assert (
            abs(init["TRANX"][0] - 2 * init_ref["TRANX"][0]) < 1e-5
        ), "Issue in TRANX with MODEL5 (NNCTRAN[0])"
        assert (
            abs(init["TRANX"][-2] - 2 * init_ref["TRANX"][0]) < 1e-5
        ), "Issue in TRANX with MODEL5 (NNCTRAN[-2])"
