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
    dic["how"] = cmdargs["approach"].strip()  # Max, min, or mode
    dic["jump"] = float(cmdargs["jump"])  # Tunning parameter
    dic["encoding"] = cmdargs["encoding"].strip()
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
        help="The base name of the input file or the name of the deck "
        "('input.txt' by default).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output",
        help="The base name of the output folder ('output' by default).",
    )
    parser.add_argument(
        "-f",
        "--flow",
        default="flow",
        help="OPM Flow full path to executable or just ('flow' by default)",
    )
    parser.add_argument(
        "-c",
        "--coarsening",
        default="2,2,2",
        help="Level of coarsening in the x, y, and z dir ('2,2,2' by default)",
    )
    parser.add_argument(
        "-a",
        "--approach",
        default="max",
        help="Use min, max, or mode to scale the actnum ('min' by default)",
    )
    parser.add_argument(
        "-j",
        "--jump",
        default=2.0,
        help="Tunning parameter to avoid creation of nnc on the structural faults "
        "('2.' by default)",
    )
    parser.add_argument(
        "-x",
        "--xcoar",
        default="",
        help="Vector of x-coarsening ('' by default)",
    )
    parser.add_argument(
        "-y",
        "--ycoar",
        default="",
        help="Vector of y-coarsening ('' by default)",
    )
    parser.add_argument(
        "-z",
        "--zcoar",
        default="",
        help="Vector of z-coarsening ('' by default)",
    )
    parser.add_argument(
        "-e",
        "--encoding",
        default="ISO-8859-1",
        help="Use 'utf8' or 'ISO-8859-1' encoding to read the deck ('ISO-8859-1' by default)",
    )
    return vars(parser.parse_known_args()[0])


def main():
    """Main function"""
    pycopm()
