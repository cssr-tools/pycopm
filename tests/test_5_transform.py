# SPDX-FileCopyrightText: 2025 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the generic submodel functionality"""

import os
import pathlib
import subprocess

dirname: pathlib.Path = pathlib.Path(__file__).parent


def test_transform():
    """See decks/MODEL0.DATA"""
    os.chdir(f"{dirname}/decks")
    flags = ["translate", "scale", "rotatexy", "rotatexz", "rotateyz"]
    values = ["[5,-3,2]", "[2,.5,4]", "45", "-10", "15"]
    for flag, val in zip(flags, values):
        subprocess.run(
            [
                "pycopm",
                "-i",
                "MODEL0.DATA",
                "-o",
                "transform",
                "-d",
                f"{flag} {val}",
                "-m",
                "all",
                "-w",
                f"{flag.upper()}",
                "-l",
                f"{flag.upper()}",
            ],
            check=True,
        )
        assert os.path.exists(f"{dirname}/decks/transform/{flag.upper()}.INIT")
        assert os.path.exists(f"{dirname}/decks/transform/{flag.upper()}.EGRID")
