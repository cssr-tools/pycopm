# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the single run functionality"""

import os
import subprocess


def test_generic_deck():
    """pycopm application to coarser a geological model given an input deck"""
    cwd = os.getcwd()
    os.chdir(f"{cwd}/tests")
    os.system("mkdir generic_deck")
    os.chdir(f"{cwd}/tests/generic_deck")
    for name in ["PERM", "PHI", "TOPS"]:
        subprocess.run(
            [
                "curl",
                "-o",
                f"./SPE10MODEL2_{name}.INC",
                "https://raw.githubusercontent.com/OPM/opm-data/master/spe10model2/"
                + f"SPE10MODEL2_{name}.INC",
            ],
            check=True,
        )
    subprocess.run(
        [
            "curl",
            "-o",
            "./SPE10_MODEL2.DATA",
            "https://raw.githubusercontent.com/OPM/opm-data/master/spe10model2/"
            + "SPE10_MODEL2.DATA",
        ],
        check=True,
    )
    subprocess.run(
        ["pycopm", "-i", "SPE10_MODEL2.DATA", "-o", "coarser", "-c", "4,8,2"],
        check=True,
    )
    os.chdir(f"{cwd}/tests/generic_deck/coarser")
    os.system("flow SPE10_MODEL2_PYCOPM.DATA --parsing-strictness=low & wait\n")
    assert os.path.exists(f"{cwd}/tests/generic_deck/coarser/SPE10_MODEL2_PYCOPM.UNRST")
    os.chdir(cwd)
