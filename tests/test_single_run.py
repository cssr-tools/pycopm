# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Test the single run functionality"""

import os
from pycopm.core.pycopm import main


def test_single_run():
    """See configs/input.txt"""
    cwd = os.getcwd()
    os.chdir(f"{cwd}/tests/configs")
    main()
    assert os.path.exists(
        f"{cwd}/tests/configs/postprocessing/wells/HISTO_DATA_WWPR_A4.png"
    )
    os.chdir(cwd)
