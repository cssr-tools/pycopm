#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""
Script to execute flow
"""

import os


def flow():
    """
    Run the simulations
    """
    os.system("${dic["flow"]} ${dic['name']}_COARSER.DATA")

if __name__ == "__main__":
    flow()
