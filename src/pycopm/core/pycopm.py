# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""Main script for pycopm"""

import os
import time
import argparse
from io import StringIO
import numpy as np
from pycopm.utils.input_values import process_input, read_reference
from pycopm.utils.grid_builder import coarser_grid
from pycopm.utils.properties_builder import coarser_properties
from pycopm.utils.files_writer import coarser_files
from pycopm.utils.runs_executer import simulations, plotting
from pycopm.utils.generate_coarser_files import create_deck


def pycopm():
    """Main function for the pycopm executable"""
    start_time = time.monotonic()
    cmdargs = load_parser()
    file = cmdargs["input"].strip()  # Name of the input file
    dic = {"fol": cmdargs["output"]}  # Name for the output folder
    dic["pat"] = os.path.dirname(__file__)[:-5]  # Path to the pycopm folder
    dic["exe"] = os.getcwd()  # Path to the folder of the input.txt file
    dic["flow"] = cmdargs["flow"].strip()  # Path to flow
    dic["how"] = cmdargs["how"].strip()  # Max, min, or mode for satnum
    dic["nhow"] = cmdargs["nhow"].strip()  # Max, min, or mode for other nums
    dic["show"] = cmdargs["show"].strip()  # Max, min, or mean for static props
    dic["jump"] = cmdargs["jump"].strip()  # Tuning parameter to remove nnc
    dic["write"] = cmdargs["write"].strip()  # Name of the generated deck
    dic["mode"] = cmdargs["mode"].strip()  # What to run
    dic["label"] = cmdargs["label"].strip()  # Prefix to the generted inc files
    dic["ijk"] = cmdargs["ijk"].strip()  # ijk indices to map to the coarse model
    dic["remove"] = int(cmdargs["remove"].strip())  # Remove CONFACT and KH
    dic["encoding"] = cmdargs["encoding"].strip()
    dic["pvcorr"] = int(cmdargs["pvcorr"])
    dic["fipcorr"] = int(cmdargs["fipcorr"])
    dic["trans"] = int(cmdargs["trans"])
    dic["cijk"] = "yes"
    for i in ["x", "y", "z"]:
        dic[f"{i}coar"] = []
        if cmdargs[f"{i}coar"]:
            dic[f"{i}coar"] = list(
                np.genfromtxt(StringIO(cmdargs[f"{i}coar"]), delimiter=",", dtype=int)
            )
            dic["cijk"] = "no"
    if dic["cijk"] != "no":
        dic["cijk"] = np.genfromtxt(
            StringIO(cmdargs["coarsening"]), delimiter=",", dtype=int
        )  # Coarsening level

    # Make the output folder
    if not os.path.exists(f"{dic['exe']}/{dic['fol']}"):
        os.system(f"mkdir {dic['exe']}/{dic['fol']}")

    # When a deck is given, then we only generate the coarser files
    if "DATA" in file:
        dic["deck"] = file.upper()[:-5]
        create_deck(dic)
        return

    # Open pycopm.utils.inputvalues to see the dic name abbreviations meaning
    process_input(dic, file)

    for folder in ["preprocessing", "parameters", "jobs", "observations"]:
        if not os.path.exists(f"{dic['exe']}/{dic['fol']}/{folder}"):
            os.system(f"mkdir {dic['exe']}/{dic['fol']}/{folder}")

    # Get the command lines for ERT
    dic["fert"] = [""]
    dic["fert"][0] += dic["ert"][0][0]
    for i in range(len(dic["ert"]) - 1):
        dic["fert"][0] += " --" + dic["ert"][i + 1][0] + " " + dic["ert"][i + 1][1]

    # Read the data from the uncoarsed output files
    read_reference(dic)

    # Coarse the grid
    coarser_grid(dic)

    # Coarse the properties defined in the deck
    coarser_properties(dic)

    # Write the files using the templates
    coarser_files(dic)

    # Copy the requeried INCLUDE files
    if dic["field"] == "drogon":
        os.system(
            f"cp -r {dic['pat']}/reference_simulation/{dic['field']}/include"
            f" {dic['exe']}/{dic['fol']}/preprocessing/include & wait"
        )
    else:
        os.system(
            f"cp -r {dic['pat']}/reference_simulation/{dic['field']}/INCLUDE"
            f" {dic['exe']}/{dic['fol']}/preprocessing/INCLUDE & wait"
        )

    # Run Flow or selected ERT functionality
    simulations(dic)

    # Make some useful plots after the studies
    plotting(dic, time.monotonic() - start_time)


def load_parser():
    """Argument options"""
    parser = argparse.ArgumentParser(
        description="Main script to coarse the geological model and run "
        "simulations using OPM Flow."
    )
    parser.add_argument(
        "-i",
        "--input",
        default="input.txt",
        help="The base name of the input file or the name of the deck, "
        "e.g., DROGON.DATA ('input.txt' by default).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=".",
        help="The base name of the output folder ('.' by "
        "default, i.e., the folder where pycopm is executed).",
    )
    parser.add_argument(
        "-f",
        "--flow",
        default="flow",
        help="OPM Flow path to executable or just 'flow' ('flow' by default).",
    )
    parser.add_argument(
        "-c",
        "--coarsening",
        default="2,2,2",
        help="Level of coarsening in the x, y, and z dir ('2,2,2' by default; "
        "either use this flag or the -x, -y, and -z ones).",
    )
    parser.add_argument(
        "-x",
        "--xcoar",
        default="",
        help="Vector of x-coarsening, e.g., if the grid has 6 cells in the x "
        "direction, then 0,2,0,2,0,2,0 would generate a coarser model with 3 "
        "cells, while 0,2,2,2,2,2,0 would generate a coarser model with 1 cell, "
        "i.e., 0 keeps the pilars while 2 removes them ('' by default).",
    )
    parser.add_argument(
        "-y",
        "--ycoar",
        default="",
        help="Vector of y-coarsening, see the description for -x ('' by default).",
    )
    parser.add_argument(
        "-z",
        "--zcoar",
        default="",
        help="Vector of z-coarsening, see the description for -x ('' by default).",
    )
    parser.add_argument(
        "-a",
        "--how",
        default="mode",
        help="Use 'min', 'max', or 'mode' to scale the actnum, e.g., min makes "
        "the new coarser cell inactive if at least one cell is inactive, while "
        " max makes it active it at least one cell is active ('mode' by default).",
    )
    parser.add_argument(
        "-n",
        "--nhow",
        default="mode",
        help="Use 'min', 'max', or 'mode' to scale endnum, eqlnum, fipnum, fluxnum, imbnum, "
        "miscnum, multnum, pvtnum, rocknum, and satnum ('mode' by default).",
    )
    parser.add_argument(
        "-s",
        "--show",
        default="",
        help="Use 'min', 'max', or 'mean' to scale permx, permy, permz, poro, swatinit, and all "
        "mult(-)xyz ('' by default, i.e., using the arithmetic average for permx/permy, harmonic"
        " average for permz, volume weighted mean for mult(-)xyz, and the pore volume weighted"
        " mean for the rest).",
    )
    parser.add_argument(
        "-p",
        "--pvcorr",
        default=0,
        help="Add the removed pore volume to the closest coarser cells ('0' by default).",
    )
    parser.add_argument(
        "-q",
        "--fipcorr",
        default=0,
        help="Adjust the pv to the initial FGIP and FOIP from the input deck ('0' by default).",
    )
    parser.add_argument(
        "-t",
        "--trans",
        default=0,
        help="Write and use upscaled transmissibilities ('0' by default, it is advice to use "
        "only with z-coarsening).",
    )
    parser.add_argument(
        "-r",
        "--remove",
        default="2",
        help="Remove CONFACT and KH from COMPDAT (1) and also remove PEQVR (2) (ITEM 13, the "
        "last entry) to compute the well transmisibility connections internally in OPM Flow "
        "using the grid properties ('2' by default; '0' to not remove).",
    )
    parser.add_argument(
        "-j",
        "--jump",
        default="",
        help="Tuning parameter to avoid creation of neighbouring connections in "
        "the coarser model where there are discontinuities between cells along "
        "the z direction, e.g., around faults ('' by default, i.e., nothing "
        "corrected; if need it, try with values of the order of 1).",
    )
    parser.add_argument(
        "-m",
        "--mode",
        default="prep_deck",
        help="Execute a dry run on the input deck to generate the static properties ('prep'), "
        "generate only the coarse files ('deck'), only exectute a dry run on the generated "
        "coarse model ('dry'), 'prep_deck', 'deck_dry', or do all ('all') ('prep_deck' by "
        "default).",
    )
    parser.add_argument(
        "-w",
        "--write",
        default="",
        help="Name of the generated deck ('' by default, i.e., the name of the input deck plus "
        "_PYCOPM.DATA).",
    )
    parser.add_argument(
        "-l",
        "--label",
        default="PYCOPM_",
        help="Added text before each generated .INC ('PYCOPM_' by default, i.e., the coarse porv "
        "is saved in PYCOPM_PORV.INC; set to '' to generate PORV.INC, PERMX.INC, etc).",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        default="ISO-8859-1",
        help="Use 'utf8' or 'ISO-8859-1' encoding to read the deck ('ISO-8859-1' by default).",
    )
    parser.add_argument(
        "-ijk",
        "--ijk",
        default="",
        help="Given i,j,k indices in the input model, return the coarse i,j,k corresponding "
        "positions ('' by default; if not empty, e.g., 1,2,3 then the -mode is set to deck and "
        "there will not be generation of coarse files, only the i,j,k coarse indices in the "
        "terminal).",
    )
    return vars(parser.parse_known_args()[0])


def main():
    """Main function"""
    pycopm()
