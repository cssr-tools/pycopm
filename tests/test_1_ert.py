# SPDX-FileCopyrightText: 2024-2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the ert functionality via the configuration file"""

import os
import pathlib
import subprocess

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_ert(flow):
    """See examples/configurations/norne/input.toml"""
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
    os.chdir(f"{testpth}/output")
    confi = f"{mainpth}/examples/configurations/norne/input.toml"
    subprocess.run(
        ["pycopm", "-i", confi, "-o", "ert", "-warnings", "1", "-f", flow], check=True
    )
    assert os.path.exists(f"{testpth}/output/ert/postprocessing/hm_missmatch.png")
