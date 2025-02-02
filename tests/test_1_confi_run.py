# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the single run functionality via the configurationf ile"""

import os
import pathlib
from pycopm.core.pycopm import main

dirname: pathlib.Path = pathlib.Path(__file__).parent


def test_single_run():
    """See configs/input.txt"""
    os.chdir(f"{dirname}/configs")
    main()
    assert os.path.exists(
        f"{dirname}/configs/postprocessing/wells/HISTO_DATA_WWPR_A4.png"
    )
