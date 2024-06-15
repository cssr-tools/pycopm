# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the ert functionality"""

import os
import subprocess


def test_ert():
    """See configs/ert.txt"""
    cwd = os.getcwd()
    os.chdir(f"{os.getcwd()}/tests/configs")
    subprocess.run(["pycopm", "-i", "ert.txt", "-o", "ert"], check=True)
    assert os.path.exists("./ert/postprocessing/hm_missmatch.png")
    os.chdir(cwd)
