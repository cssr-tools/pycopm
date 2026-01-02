# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
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
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid
from opm.io.ecl import ERst as OpmRestart


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
    dic["flowflag"] = dic["flow"]
    with open(in_file, "rb") as file:
        dic.update(tomllib.load(file))
    if dic["field"] == "norne":
        dic["name"] = "NORNE_ATW2013"
    else:
        dic["name"] = "DROGON"
    for val in ["X", "Y", "Z"]:
        dic[val] = np.array(dic[val])
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
    flowtoml = subprocess.call(
        dic["flowpth"].strip(),
        shell=True,
        stderr=subprocess.STDOUT,
        stdout=subprocess.DEVNULL,
    )
    flowflag = subprocess.call(
        dic["flowflag"],
        shell=True,
        stderr=subprocess.STDOUT,
        stdout=subprocess.DEVNULL,
    )
    if flowtoml != 1 and flowflag != 1:
        print(
            f"\nThe OPM flow executable '{dic['flowpth'].strip()}' is not found; "
            "try to install it following the pycopm documentation.\nIf it was "
            "built from source, then either add the folder location to your path, "
            "or write the path\nto flow in the toml configuration file "
            "(e.g., flow = '/home/pycopm/build/opm-simulators/bin/flow'),\n"
            "or using the command flag -f or --flow.\n"
        )
        sys.exit()
    if flowtoml != 1:
        dic["flow"] = dic["flow"].split()
        for i, value in enumerate(dic["flow"]):
            if "flow" in value:
                dic["flow"][i] = dic["flowflag"]
                break
        dic["flow"] = " ".join(dic["flow"])


def read_reference(dic):
    """
    Function to read the cell quantities from the uncoarsened simulation output.

    Args:
        dic (dict): Global dictionary with required parameters

    Returns:
        dic (dict): Modified global dictionary

    """
    initialize_values(dic)
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
    gri, ini = dic["case"] + ".EGRID", dic["case"] + ".INIT"
    rst = dic["case"] + ".UNRST"
    grid, gridf, ini, rst = OpmGrid(gri), OpmFile(gri), OpmFile(ini), OpmRestart(rst)
    if dic["field"] == "norne":
        values = ["PORO", "NTG", "SWL", "SGU", "SWCR", "FLUXNUM", "FIPNUM"]
    else:
        values = [
            "PORO",
            "NTG",
            "SWL",
            "SGU",
            "SWCR",
            "FIPNUM",
            "MULTNUM",
            "PVTNUM",
        ]
    values += ["EQLNUM", "PERMX", "PERMY", "PERMZ", "SATNUM"]
    dic["nc"] = grid.dimension[0] * grid.dimension[1] * grid.dimension[2]
    dic["nd"] = [grid.dimension[0], grid.dimension[1], grid.dimension[2]]
    dic["i_f_c"] = np.array([0 for _ in range(dic["nd"][0] + 1)])
    dic["j_f_c"] = np.array([0 for _ in range(dic["nd"][1] + 1)])
    dic["k_f_c"] = np.array([0 for _ in range(dic["nd"][2] + 1)])
    for name in ["vol", "poro", "permx", "permy", "permz", "ntg", "swl"]:
        dic[f"{name}"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["sgu"] = np.array([0.0 for _ in range(dic["nc"])])
    dic["swcr"] = np.array([0.0 for _ in range(dic["nc"])])
    for name in ["con", "actnum", "fluxnum", "multnum", "fipnum"]:
        dic[f"{name}"] = np.array([0 for _ in range(dic["nc"])])
    dic["eqlnum"] = np.array([0 for _ in range(dic["nc"])])
    dic["multz"] = np.array([1.0 for _ in range(dic["nc"])])
    dic["satnum"] = np.array([1 for _ in range(dic["nc"])])
    dic["pvtnum"] = np.array([1 for _ in range(dic["nc"])])
    dic["fipzon"] = np.array([1 for _ in range(dic["nc"])])
    dic["zc"], dic["cr"] = gridf["ZCORN"], gridf["COORD"]
    dic["vol"] = np.array(grid.cellvolumes()) + 1e-10
    dic["actnum"] = np.array(ini["PORV"]) > 0
    for name in ["swat", "sgas", "pressure", "rs", "rv"]:
        dic[name] = np.array([0.0 for _ in range(dic["nc"])])
        dic[name][dic["actnum"]] = rst[name.upper(), 0]
    for name in values:
        dic[name.lower()][dic["actnum"]] = ini[name]
