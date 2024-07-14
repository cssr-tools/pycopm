# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""
Utiliy functions to set the requiried input values by pycopm.
"""

from io import StringIO
import csv
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
    lol = []
    with open(in_file, "r", encoding="utf8") as file:
        for row in csv.reader(file, delimiter="#"):
            lol.append(row)
    inc = read_the_first_part(lol, dic)
    num_lin = get_number_of_lines(lol, inc)
    ind = assign_standard_values(lol, dic, inc, num_lin)
    assign_hm_parameters(lol, dic, ind)


def read_the_first_part(lol, dic):
    """
    Function to process the first 29 lines of the input file

    Args:
        lol (list): List of lines read from the input file\n
        dic (dict): Global dictionary with required parameters

    Returns:
        inc (int): Number of line in the input file before the first injection value
    """
    dic["flow"] = str(lol[1])[2:-2]  # Path to the flow executable
    dic["suffixes"] = str(lol[4])[4:-4]  # Suffixes to delete after simulations
    dic["field"] = str(lol[7][0])  # Geological model (norne or drogon)
    if dic["field"][0:5] == str("norne"):
        dic["field"] = "norne"
        dic["name"] = "NORNE_ATW2013"
    elif dic["field"][0:6] == str("drogon"):
        dic["field"] = "drogon"
        dic["name"] = "DROGON"
    dic["study"] = str(lol[8][0])  # Type of study to run (single-run or ert)
    if dic["study"][0:10] == str("single-run"):
        dic["study"] = 0
    elif dic["study"][0:3] == str("ert"):
        dic["study"] = 1
    x_1 = np.genfromtxt(StringIO(lol[9][0][1:]), delimiter=" ", dtype=int)
    x_2 = np.genfromtxt(StringIO(lol[10][0][:-2]), delimiter=" ", dtype=int)
    dic["X"] = np.concatenate((x_1, x_2))
    y_1 = np.genfromtxt(StringIO(lol[11][0][1:]), delimiter=" ", dtype=int)
    y_2 = np.genfromtxt(StringIO(lol[12][0]), delimiter=" ", dtype=int)
    y_3 = np.genfromtxt(StringIO(lol[13][0]), delimiter=" ", dtype=int)
    y_4 = np.genfromtxt(StringIO(lol[14][0]), delimiter=" ", dtype=int)
    y_5 = np.genfromtxt(StringIO(lol[15][0][:-2]), delimiter=" ", dtype=int)
    dic["Y"] = np.concatenate((y_1, y_2, y_3, y_4, y_5))
    dic["Z"] = np.genfromtxt(StringIO(lol[16][0][1:-2]), delimiter=" ", dtype=int)
    dic["Ne"] = int(lol[17][0])  # Number of ensembles
    dic["Mr"] = int(lol[18][0])  # Maximum Number of ensembles running in paralell
    dic["mpi"] = int(lol[19][0])  # Number of mpi processes to run flow
    dic["mrt"] = int(lol[20][0])  # Maximum runtime in seconds of a realization.
    dic["mrn"] = int(lol[21][0])  # Minimum number of succeeded realizations.
    dic["rds"] = int(lol[22][0])  # Set a specific seed for reproducibility.
    dic["Obs"] = str(lol[23][0]).replace(
        " ", ""
    )  # Name of the observation file for the hm
    dic["deck"] = int(lol[24][0])  # Select which coarser deck to use: 0 or 1
    dic["CS"] = int(lol[25][0])  # For the LET coarser deck, select: 0, 1, or 2
    dic["PV"] = int(lol[26][0])  # Select: 0, 1, or 2
    dic["initial"] = int(lol[27][0])  # Select: 0, 1,
    dic["error"] = np.genfromtxt(
        StringIO(lol[28][0]), delimiter=" ", dtype=float
    )  # Error WOPR, WGPR, and WWPR
    dic["minerror"] = np.genfromtxt(
        StringIO(lol[29][0]), delimiter=" ", dtype=float
    )  # Minimum error of WOPR, WGPR, and WWPR
    dic["date"] = str(lol[30][0]).replace(" ", "")  # Last date to HM
    inc = 34  # Increase this if more rows are added to the input text file
    return inc


def get_number_of_lines(lol, inc):
    """
    Function to obtain the number of OPM and ERT flags

    Args:
        lol (list): List of lines read from the input file\n
        inc (int): Number of line in the input file before the first injection value

    Returns:
        num_lin (list): List with the number of opm flags, and ert flags
    """
    num_lin = [0 for i in range(2)]
    nol = len(lol)
    for i in range(nol):
        if i > inc:
            num_lin[0] += 1
            if not lol[i]:
                break
    for i in range(nol):
        if i > inc + num_lin[0] + 3:
            num_lin[1] += 1
            if not lol[i]:
                break
    return num_lin


def assign_standard_values(lol, dic, inc, num_lin):
    """
    Function to process the ert and opm flags

    Args:
        lol (list): List of lines read from the input file\n
        dic (dict): Global dictionary with required parameters\n
        inc (int): Number of line in input file before the first injection value\n
        num_lin (list): List with the number of opm  and ert flags

    Returns:
        ind (int): Number of line of the last opm flags in the input file
    """
    column = []
    for i in range(num_lin[0]):  # ERT command line values
        row = list((lol[inc + i][0].strip()).split())
        if len(row) == 1:
            column.append(
                [
                    str(row[0]),
                ]
            )
        else:
            column.append(
                [
                    str(row[0]),
                    str(row[1]),
                ]
            )
    dic["ert"] = column
    column = []
    ind = inc + num_lin[0] + 3
    for i in range(num_lin[1]):  # Flow flag values
        row = list((lol[ind + i][0].strip()).split())
        column.append(
            [
                str(row[0]),
                str(row[1]),
            ]
        )
    dic["flag"] = column
    ind += num_lin[1] + 3
    return ind


def assign_hm_parameters(lol, dic, ind):
    """
    Function to process the saturation functions

    Args:
        lol (list): List of lines read from the input file\n
        dic (dict): Global dictionary with required parameters\n
        ind (int): Number of line of the last opm flags in the input file

    Returns:
        dic (dict): Modified global dictionary

    """
    column = []
    nlet = 18
    for i in range(nlet):  # Saturation function values
        row = list((lol[ind + i][0].strip()).split())
        column.append(
            [
                str(row[0]),
                float(row[1]),
                int(row[2]),
                str(row[3]),
                float(row[4]),
                float(row[5]),
            ]
        )
    dic["LET"] = column
    column = []
    ind += nlet + 3
    for i in range(3):  # Rock permeability hm settings
        row = list((lol[ind + i][0].strip()).split())
        column.append(
            [
                str(row[0]),
                int(row[1]),
                str(row[2]),
            ]
        )
    dic["rock"] = column


def read_reference(dic):
    """
    Function to read the cell quantities from the uncoarser simulation output.

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
    if dic["field"] == "drogon" and dic["CS"] > 0:
        if dic["CS"] == 1:
            lol = []
            with open(
                f"{dic['pat']}/reference_simulation/{dic['field']}/satnum_5.out",
                "r",
                encoding="utf8",
            ) as file:
                for row in csv.reader(file, delimiter="#"):
                    lol.append(int(row[0]))
        elif dic["CS"] == 3:
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
