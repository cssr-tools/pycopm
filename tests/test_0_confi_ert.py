# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the ert functionality via the configuration file"""

import os
import pathlib
import subprocess

dirname: pathlib.Path = pathlib.Path(__file__).parent


def test_ert():
    """See configs/ert.txt"""
    os.chdir(f"{dirname}/configs")
    subprocess.run(["pycopm", "-i", "ert.txt", "-o", "ert"], check=True)
    assert os.path.exists(f"{dirname}/configs/ert/postprocessing/hm_missmatch.png")
