# SPDX-FileCopyrightText: 2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801,R0914

"""Test the coarsening by transmissibilities"""

import os
import pathlib
import subprocess
from opm.io.ecl import EclFile as OpmFile

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_transmissibilities(flow):
    """See examples/decks/MODEL4.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    subprocess.run(
        [
            flow,
            f"{mainpth}/examples/decks/MODEL4.DATA",
            f"--output-dir={testpth}/output/transmissibilities",
        ],
        check=True,
    )
    values = [
        [523.75178, 706.33996, 5008.1327, 106.21933],
        [523.75178, 706.33996, 0, 106.21933],
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
                abs(sum(init[f"TRAN{n}"]) - values[i][j]) < 1e-2
            ), f"Issue in TRAN{n} with -t {i}"
