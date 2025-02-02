# SPDX-FileCopyrightText: 2025 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the generic refinement functionality"""

import os
import pathlib
import subprocess

dirname: pathlib.Path = pathlib.Path(__file__).parent


def test_refinement():
    """See decks/HELLO_WORLD.DATA"""
    os.chdir(f"{dirname}/decks")
    subprocess.run(
        [
            "pycopm",
            "-o",
            "finer",
            "-i",
            "HELLO_WORLD.DATA",
            "-g",
            "5,4,1",
            "-w",
            "FINER",
            "-m",
            "all",
        ],
        check=True,
    )
    assert os.path.exists(f"{dirname}/decks/finer/FINER.INIT")
    assert os.path.exists(f"{dirname}/decks/finer/FINER.EGRID")
