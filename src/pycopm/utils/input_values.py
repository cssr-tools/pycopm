# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""
Utiliy functions to set the input values from the toml configuration file.
"""

import csv
import sys
import tomllib
import subprocess
from itertools import islice
import numpy as np
from resdata.grid import Grid
from resdata.resfile import ResdataFile


def process_input(dic, in_file):
    """
    Function to process the input file

    Args:
        dic (dict): Global dictionary with required parameters\n
        in_file (str): Name of the input text file

    Returns:
        dic (dict): Modified global dictionary
    """
    dic["letsatn"] = 0
    dic["suffixes"] = ""
    with open(in_file, "rb") as file:
        dic.update(tomllib.load(file))
    if dic["field"] == "norne":
        dic["name"] = "NORNE_ATW2013"
    else:
        dic["name"] = "DROGON"
    for val in ["X", "Y", "Z"]:
        dic[val] = np.array(dic[val])
    dic["ert"] = dic["ert"].split(" ")
    dic["suffixes"] = ",".join(["'" + val + "'" for val in dic["suffixes"]])
    check_flow(dic, in_file)


def check_flow(dic, in_file):
    """
    Check if flow is found

    Args:
        dic (dict): Global dictionary with required parameters\n
        in_file (str): Name of the input text file

    Returns:
        dic (dict): Modified global dictionary
    """
    dic["flowpth"] = False
    for value in dic["flow"].split():
        if "flow" in value:
            dic["flowpth"] = value
            break
    if not dic["flowpth"]:
        print(
            f"\nflow is not included in the configuration file {in_file}.\n"
            "See the pycopm documentation.\n"
        )
        sys.exit()
    if (
        subprocess.call(
            dic["flowpth"].strip(),
            shell=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.DEVNULL,
        )
        != 1
    ):
        print(
            f"\nThe OPM flow executable '{dic['flowpth'].strip()}' is not found; "
            "try to install it following the pycopm documentation.\nIf it was "
            "built from source, then either add the folder location to your path, "
            "or write the path\nto flow in the toml configuration file "
            "(e.g., flow = '/home/pycopm/build/opm-simulators/bin/flow').\n"
        )
        sys.exit()


def read_reference(dic):
    """
    Function to read the cell quantities from the uncoarsened simulation output.

    Args:
        dic (dict): Global dictionary with required parameters

    Returns:
        dic (dict): Modified global dictionary

    """
    dic1 = initialize_values(dic)
    j = 0
    for cell in dic["grid"].cells():
        dic["vol"][cell.global_index] = cell.volume + 1e-10
        dic["actnum"][cell.global_index] = cell.active
        if cell.active == 1:
            dic["swat"][cell.global_index] = dic1["swat"][0][j]
            dic["sgas"][cell.global_index] = dic1["sgas"][0][j]
            dic["pressure"][cell.global_index] = dic1["pressure"][0][j]
            dic["rs"][cell.global_index] = dic1["rs"][0][j]
            dic["rv"][cell.global_index] = dic1["rv"][0][j]

            for name in dic1["names"]:
                dic[name.lower()][cell.global_index] = dic1[name][0][j]
            j += 1
    if dic["field"] == "norne":
        dic["multz"] = np.load(
            f"{dic['pat']}/reference_simulation/{dic['field']}/multz.npy"
        )
        dic["satnum"] = np.load(
            f"{dic['pat']}/reference_simulation/{dic['field']}/satnum.npy"
        )
    if dic["field"] == "drogon" and dic["letsatn"] > 0:
        if dic["letsatn"] == 1:
            lol = []
            with open(
                f"{dic['pat']}/reference_simulation/{dic['field']}/satnum_5.out",
                "r",
                encoding="utf8",
            ) as file:
                for row in csv.reader(file, delimiter="#"):
                    lol.append(int(row[0]))
        elif dic["letsatn"] == 3:
            lol = []
            with open(
                f"{dic['pat']}/reference_simulation/{dic['field']}/satnum_60.out",
                "r",
                encoding="utf8",
            ) as file:
                for row in csv.reader(file, delimiter="#"):
                    lol.append(int(row[0]))
        dic["satnum"] = np.array(lol)
    faults = []
    if dic["field"] == "drogon":
        with open(
            f"{dic['pat']}/reference_simulation/{dic['field']}/include/grid/drogon.faults",
            "r",
            encoding="utf8",
        ) as file:
            for row in islice(
                csv.reader(file, skipinitialspace=True, delimiter=" "), 19, 170
            ):
                faults.append(row[1:8])
    dic["fault"] = faults


def initialize_values(dic):
    """
    Function to initialize the dic variables.

    Args:
        dic (dict): Global dictionary with required parameters

    Returns:
        dic1 (dict): Local dictionary

    """
    dic["case"] = dic["pat"] + f"/reference_simulation/{dic['field']}/{dic['name']}"
    grid, ini = dic["case"] + ".EGRID", dic["case"] + ".INIT"
    rst = dic["case"] + ".UNRST"
    dic["grid"], ini, rst = Grid(grid), ResdataFile(ini), ResdataFile(rst)
    dic1 = {
        "swat": rst.iget_kw("SWAT"),
        "sgas": rst.iget_kw("SGAS"),
        "pressure": rst.iget_kw("PRESSURE"),
        "rs": rst.iget_kw("RS"),
        "rv": rst.iget_kw("RV"),
    }
    if dic["field"] == "norne":
        dic1["names"] = ["PORO", "NTG", "SWL", "SGU", "SWCR", "FLUXNUM", "FIPNUM"]
    else:
        dic1["names"] = [
            "PORO",
            "NTG",
            "SWL",
            "SGU",
            "SWCR",
            "FIPNUM",
            "MULTNUM",
            "PVTNUM",
        ]
    dic1["names"] += ["EQLNUM", "PERMX", "PERMY", "PERMZ", "SATNUM"]
    for ent in dic1["names"]:
        dic1[ent] = ini.iget_kw(ent)
    dic["nc"] = dic["grid"].nx * dic["grid"].ny * dic["grid"].nz
    dic["i_f_c"] = np.array([0 for _ in range(dic["grid"].nx + 1)])
    dic["j_f_c"] = np.array([0 for _ in range(dic["grid"].ny + 1)])
    dic["k_f_c"] = np.array([0 for _ in range(dic["grid"].nz + 1)])
    for name in ["vol", "poro", "permx", "permy", "permz", "ntg", "swl"]:
        dic[f"{name}"] = np.array([0.0 for _ in range(dic["nc"])])
    for name in ["con", "actnum", "fluxnum", "multnum", "fipnum"]:
        dic[f"{name}"] = np.array([0 for _ in range(dic["nc"])])
    dic["eqlnum"] = np.array([0 for _ in range(dic["nc"])])
    dic["sgu"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["swcr"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["swat"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["sgas"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["rs"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["rv"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["pressure"] = np.array([0.0 for _ in range(dic["nc"])])

    dic["multz"] = np.array([1.0 for _ in range(dic["nc"])])
    dic["satnum"] = np.array([1 for _ in range(dic["nc"])])
    dic["pvtnum"] = np.array([1 for _ in range(dic["nc"])])
    dic["fipzon"] = np.array([1 for _ in range(dic["nc"])])
    dic["zc"], dic["cr"] = dic["grid"].export_zcorn(), dic["grid"].export_coord()
    return dic1
