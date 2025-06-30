#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""
Script to get the simulation time
"""

import os
import csv


def get_time_simulation():
    """
    Get the simulation time from the debug file
    """

    dbgName = "${dic['name']}_COARSER.DBG"
    if os.path.isfile(dbgName) == 1:
        solData = []
        try:
            for row in csv.reader(open(dbgName), delimiter=":"):
                solData.append(row)
            with open("time_sim.txt", 'w') as file:
                file.write(f'{float(solData[-23][-1])}')
        except:
            print(f'Problem with the DBG file')

if __name__ == "__main__":
    get_time_simulation()
