# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the ert functionality via the configuration file"""

import os
import pathlib
import subprocess

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_ert():
    """See examples/configurations/norne/coarser.txt"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    os.chdir(f"{testpth}/output")
    confi = f"{mainpth}/examples/configurations/norne/coarser.txt"
    subprocess.run(["pycopm", "-i", confi, "-o", "ert"], check=True)
    assert os.path.exists(f"{testpth}/output/ert/postprocessing/hm_missmatch.png")
