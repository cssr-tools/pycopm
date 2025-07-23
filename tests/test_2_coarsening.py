# SPDX-FileCopyrightText: 2024-2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0801

"""Test the generic coarsening functionality"""

import os
import pathlib
import subprocess
import warnings

OPM = False
try:
    OPM = bool(__import__("opm"))
except ImportError:
    warnings.warn(
        UserWarning(
            "The optional OPM Python package for postprocessing "
            "the simulation files is not found; then, test_2_coarsening.py is only run "
            "using resdata."
        )
    )

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_coarsening():
    """See examples/decks/HELLO_WORLD.DATA"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    readers = ["resdata"]
    if OPM:
        readers += ["opm"]
    for use in readers:
        sub = f"FINER{use.upper()}"
        subprocess.run(
            [
                "pycopm",
                "-c",
                "5,5,1",
                "-i",
                f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
                "-o",
                f"{testpth}/output/coarser",
                "-warnings",
                "1",
                "-m",
                "prep",
                "-u",
                use,
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
                            "5,5,1",
                            "-m",
                            "deck",
                            "-a",
                            ahow,
                            "-n",
                            nhow,
                            "-warnings",
                            "1",
                            "-s",
                            show,
                            "-u",
                            use,
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
                "-warnings",
                "1",
                "-x",
                "6:10",
                "-y",
                "0,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,2,2,0,0,0",
                "-w",
                sub,
                "-u",
                use,
            ],
            check=True,
        )
        assert os.path.exists(f"{testpth}/output/coarser/{sub}.INIT")
        assert os.path.exists(f"{testpth}/output/coarser/{sub}.EGRID")
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
                "-o",
                f"{testpth}/output/coarser",
                "-c",
                "1,5,1",
                "-m",
                "deck_dry",
                "-t",
                "1",
                "-warnings",
                "1",
                "-w",
                f"TRANS{sub}",
                "-u",
                use,
            ],
            check=True,
        )
        assert os.path.exists(f"{testpth}/output/coarser/TRANS{sub}.INIT")
        assert os.path.exists(f"{testpth}/output/coarser/TRANS{sub}.EGRID")
        subprocess.run(
            [
                "pycopm",
                "-i",
                f"{mainpth}/examples/decks/HELLO_WORLD.DATA",
                "-o",
                f"{testpth}/output/coarser",
                "-c",
                "5,1,4",
                "-m",
                "deck_dry",
                "-t",
                "2",
                "-w",
                f"TRANS2{sub}",
                "-u",
                use,
                "-warnings",
                "1",
            ],
            check=True,
        )
        assert os.path.exists(f"{testpth}/output/coarser/TRANS2{sub}.INIT")
        assert os.path.exists(f"{testpth}/output/coarser/TRANS2{sub}.EGRID")
