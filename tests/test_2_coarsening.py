# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic coarsening functionality"""

import os
import pathlib
import subprocess

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_coarsening():
    """See examples/decks/HELLO_WORLD.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    subprocess.run(
        [
            "pycopm",
            "-c",
            "5,1,5",
            "-i",
            f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
            "-o",
            f"{testpth}/output/coarser",
            "-m",
            "prep",
        ],
        check=True,
    )
    assert os.path.exists(
        f"{testpth}/output/coarser/HELLO_WORLD_PREP_PYCOPM_DRYRUN.INIT"
    )
    assert os.path.exists(
        f"{testpth}/output/coarser/HELLO_WORLD_PREP_PYCOPM_DRYRUN.EGRID"
    )
    for ahow in ["max", "min", "mode"]:
        for nhow in ["max", "min", "mode"]:
            for show in ["max", "min", "mean", "pvmean"]:
                subprocess.run(
                    [
                        "pycopm",
                        "-i",
                        f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
                        "-o",
                        f"{testpth}/output/coarser",
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
                    f"{testpth}/output/coarser/HELLO_WORLD_PYCOPM.DATA"
                )
                os.system(f"rm {testpth}/output/coarser/HELLO_WORLD_PYCOPM.DATA")
    subprocess.run(
        [
            "pycopm",
            "-i",
            f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
            "-o",
            f"{testpth}/output/coarser",
            "-m",
            "deck_dry",
            "-p",
            "1",
            "-n",
            "mode",
            "-x",
            "6:10",
            "-z",
            "0,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,2,2,0,0,0",
        ],
        check=True,
    )
    assert os.path.exists(f"{testpth}/output/coarser/HELLO_WORLD_PYCOPM.INIT")
    assert os.path.exists(f"{testpth}/output/coarser/HELLO_WORLD_PYCOPM.EGRID")
    subprocess.run(
        [
            "pycopm",
            "-i",
            f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
            "-o",
            f"{testpth}/output/coarser",
            "-c",
            "1,1,5",
            "-m",
            "deck_dry",
            "-t",
            "1",
            "-w",
            "TRANS",
        ],
        check=True,
    )
    assert os.path.exists(f"{testpth}/output/coarser/TRANS.INIT")
    assert os.path.exists(f"{testpth}/output/coarser/TRANS.EGRID")
    subprocess.run(
        [
            "pycopm",
            "-i",
            f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
            "-o",
            f"{testpth}/output/coarser",
            "-c",
            "5,4,1",
            "-m",
            "deck_dry",
            "-t",
            "2",
            "-w",
            "TRANS2",
        ],
        check=True,
    )
    assert os.path.exists(f"{testpth}/output/coarser/TRANS2.INIT")
    assert os.path.exists(f"{testpth}/output/coarser/TRANS2.EGRID")
