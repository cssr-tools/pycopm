# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the single run functionality"""

import os
import subprocess


def test_generic_deck():
    """pycopm application to coarser a geological model given an input deck"""
    cwd = os.getcwd()
    os.chdir(f"{os.getcwd()}/tests/decks")
    subprocess.run(
        [
            "pycopm",
            "-i",
            "HELLO_WORLD.DATA",
            "-o",
            "coarser",
            "-c",
            "5,1,5",
            "-m",
            "prep",
        ],
        check=True,
    )
    assert os.path.exists(
        f"{cwd}/tests/decks/coarser/HELLO_WORLD_PREP_PYCOPM_DRYRUN.INIT"
    )
    assert os.path.exists(
        f"{cwd}/tests/decks/coarser/HELLO_WORLD_PREP_PYCOPM_DRYRUN.EGRID"
    )
    for ahow in ["max", "min", "mode"]:
        for nhow in ["max", "min", "mode"]:
            for show in ["max", "min", "mean"]:
                subprocess.run(
                    [
                        "pycopm",
                        "-i",
                        "HELLO_WORLD.DATA",
                        "-o",
                        "coarser",
                        "-c",
                        "5,1,5",
                        "-m",
                        "deck",
                        "-a",
                        ahow,
                        "-n",
                        nhow,
                        "-s",
                        show,
                    ],
                    check=True,
                )
                assert os.path.exists(
                    f"{cwd}/tests/decks/coarser/HELLO_WORLD_PYCOPM.DATA"
                )
                os.system(f"rm {cwd}/tests/decks/coarser/HELLO_WORLD_PYCOPM.DATA")
    subprocess.run(
        [
            "pycopm",
            "-i",
            "HELLO_WORLD.DATA",
            "-o",
            "coarser",
            "-m",
            "deck_dry",
            "p",
            "1",
            "-n",
            "mode",
            "-x",
            "0,0,0,0,0,2,2,2,2,2,0,0,0,0,0,0,0,0,0,0,0",
            "-z",
            "0,0,0,0,0,0,0,0,0,0,0,0,0,2,2,2,2,2,0,0,0",
        ],
        check=True,
    )
    assert os.path.exists(f"{cwd}/tests/decks/coarser/HELLO_WORLD_PYCOPM.INIT")
    assert os.path.exists(f"{cwd}/tests/decks/coarser/HELLO_WORLD_PYCOPM.EGRID")
    os.chdir(cwd)
