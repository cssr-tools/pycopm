# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the configuration files"""

import os
import pathlib
from pycopm.core.pycopm import main

testpth: pathlib.Path = pathlib.Path(__file__).parent
mainpth: pathlib.Path = pathlib.Path(__file__).parents[1]


def test_main():
    """See examples/configurations/drogon/input.toml"""
    confi = f"{mainpth}/examples/configurations/drogon/input.toml"
    if not os.path.exists(f"{testpth}/output"):
        os.system(f"mkdir {testpth}/output")
        os.system(f"mkdir {testpth}/output/main")
        os.system(f"cp {confi} {testpth}/output/main/input.toml")
    elif not os.path.exists(f"{testpth}/output/main"):
        os.system(f"mkdir {testpth}/output/main")
        os.system(f"cp {confi} {testpth}/output/main/input.toml")
    elif not os.path.isfile(f"{testpth}/output/main/input.toml"):
        os.system(f"cp {confi} {testpth}/output/main/input.toml")
    os.chdir(f"{testpth}/output/main")
    main()
    assert os.path.exists(
        f"{testpth}/output/main/postprocessing/wells/HISTO_DATA_WWPR_A4.png"
    )
