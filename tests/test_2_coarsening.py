# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the generic coarsening functionality"""

from pathlib import Path
import subprocess


def test_2_coarsening(flow, tmp_path, monkeypatch):
    """See examples/decks/HELLO_WORLD.DATA"""
    repo_root = Path(__file__).parents[1]
    monkeypatch.chdir(tmp_path)
    sub = "FINER"
    subprocess.run(
        [
            "pycopm",
            "-f",
            flow,
            "-c",
            "5,5,1",
            "-i",
            f"{repo_root}/examples/decks/HELLO_WORLD.DATA",
            "-m",
            "prep",
        ],
        check=True,
    )
    assert (tmp_path / "HELLO_WORLD_PREP_PYCOPM_DRYRUN.INIT").is_file()
    assert (tmp_path / "HELLO_WORLD_PREP_PYCOPM_DRYRUN.EGRID").is_file()
    for ahow in ["max", "min", "mode"]:
        for nhow in ["max", "min", "mode"]:
            for show in ["max", "min", "mean", "pvmean"]:
                subprocess.run(
                    [
                        "pycopm",
                        "-f",
                        flow,
                        "-i",
                        f"{repo_root}/examples/decks/HELLO_WORLD.DATA",
                        "-c",
                        "5,5,1",
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
                assert (tmp_path / "HELLO_WORLD_PYCOPM.DATA").is_file()
                subprocess.run(["rm", "HELLO_WORLD_PYCOPM.DATA"], check=True)
    subprocess.run(
        [
            "pycopm",
            "-f",
            flow,
            "-i",
            f"{repo_root}/examples/decks/HELLO_WORLD.DATA",
            "-m",
            "deck_dry",
            "-p",
            "1",
            "-n",
            "mode",
            "-x",
            "6:10",
            "-y",
            "0,2,2,2,0,0,0,0,0,0,0,0,2,2,2,2,2,2,0,0,0",
            "-w",
            sub,
        ],
        check=True,
    )
    assert (tmp_path / f"{sub}.INIT").is_file()
    assert (tmp_path / f"{sub}.EGRID").is_file()
    subprocess.run(
        [
            "pycopm",
            "-f",
            flow,
            "-i",
            f"{repo_root}/examples/decks/HELLO_WORLD.DATA",
            "-c",
            "1,5,1",
            "-m",
            "deck_dry",
            "-t",
            "1",
            "-w",
            f"TRANS{sub}",
        ],
        check=True,
    )
    assert (tmp_path / f"TRANS{sub}.INIT").is_file()
    assert (tmp_path / f"TRANS{sub}.EGRID").is_file()
    subprocess.run(
        [
            "pycopm",
            "-f",
            flow,
            "-i",
            f"{repo_root}/examples/decks/HELLO_WORLD.DATA",
            "-c",
            "5,1,4",
            "-m",
            "deck_dry",
            "-t",
            "2",
            "-w",
            f"TRANS2{sub}",
        ],
        check=True,
    )
    assert (tmp_path / f"TRANS2{sub}.INIT").is_file()
    assert (tmp_path / f"TRANS2{sub}.EGRID").is_file()
