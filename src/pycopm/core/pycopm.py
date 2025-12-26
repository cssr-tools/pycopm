# SPDX-FileCopyrightText: 2024-2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0915,R1702

"""Main script for pycopm"""

import os
import time
import sys
import argparse
import warnings
from io import StringIO
import subprocess
import numpy as np
from pycopm.utils.input_values import process_input, read_reference
from pycopm.utils.grid_builder import coarser_grid
from pycopm.utils.properties_builder import coarser_properties
from pycopm.utils.files_writer import coarser_files
from pycopm.utils.runs_executer import simulations, plotting
from pycopm.utils.generate_files import create_deck


def pycopm():
    """Main function for the pycopm executable"""
    start_time = time.monotonic()
    cmdargs = load_parser()
    check_cmdargs(cmdargs)
    file = cmdargs["input"].strip()  # Name of the input file
    dic = {"fol": os.path.abspath(cmdargs["output"])}  # Name for the output folder
    dic["pat"] = os.path.dirname(__file__)[:-5]  # Path to the pycopm folder
    dic["flow"] = cmdargs["flow"].strip()  # Path to flow
    dic["how"] = (cmdargs["how"].strip()).split(",")  # Max, min, or mode for actnum
    dic["nhow"] = cmdargs["nhow"].strip()  # Max, min, or mode for other nums
    dic["show"] = cmdargs["show"].strip()  # Max, min, or mean for static props
    dic["jump"] = (cmdargs["jump"].strip()).split(",")  # Tuning to remove nnc
    dic["write"] = cmdargs["write"].strip()  # Name of the generated deck
    dic["mode"] = cmdargs["mode"].strip()  # What to run
    dic["label"] = cmdargs["label"].strip()  # Prefix to the generted inc files
    dic["ijk"] = cmdargs["ijk"].strip()  # ijk indices to map to the modified model
    dic["remove"] = int(cmdargs["remove"].strip())  # Remove CONFACT and KH
    dic["encoding"] = cmdargs["encoding"].strip()  # Use utf8 or ISO-8859-1
    dic["pvcorr"] = int(cmdargs["pvcorr"])  # Correct for removed pore volume
    dic["fipcorr"] = int(cmdargs["fipcorr"])  # Correct for total mass of fluids
    dic["trans"] = int(cmdargs["trans"])  # Coarse transmissibilities
    dic["vicinity"] = cmdargs["vicinity"].strip()  # Extract sub models
    dic["transform"] = cmdargs["displace"].strip()  # Apply affine transformations
    dic["explicit"] = int(cmdargs["explicit"]) == 1  # Write cell values in the SOLUTION
    dic["warnings"] = int(cmdargs["warnings"]) == 1  # Show or hidde python warnings
    if not dic["warnings"]:
        warnings.warn = lambda *args, **kwargs: None
    for label, name, tag in zip(["", "r"], ["coarsening", "gridding"], ["coar", "ref"]):
        dic[f"{label}cijk"] = "yes"
        for i in ["x", "y", "z"]:
            dic[f"{i}{tag}"] = []
            if cmdargs[f"{i}{tag}"]:
                if ":" in cmdargs[f"{i}{tag}"]:
                    dic[f"{i}{tag}"] = [0]
                    ind = 1
                    for val in cmdargs[f"{i}{tag}"].split(","):
                        ent = val.split(":")
                        for _ in range(ind, int(ent[0])):
                            dic[f"{i}{tag}"] += [0]
                        if len(ent) > 1:
                            for _ in range(int(ent[0]), int(ent[1])):
                                dic[f"{i}{tag}"] += [2]
                            ind = int(ent[1])
                        else:
                            ind = int(ent[0])
                    dic[f"{i}{tag}"] += [0]
                else:
                    dic[f"{i}{tag}"] = list(
                        np.genfromtxt(
                            StringIO(cmdargs[f"{i}{tag}"]), delimiter=",", dtype=int
                        )
                    )
                dic[f"{label}cijk"] = "no"
        if dic[f"{label}cijk"] != "no" and cmdargs[name]:
            dic[f"{label}cijk"] = np.genfromtxt(
                StringIO(cmdargs[name]), delimiter=",", dtype=int
            )
    if (
        not isinstance(dic["rcijk"], str)
        or sum(len(dic[f"{i}ref"]) for i in ["x", "y", "z"]) > 0
    ):
        dic["refinement"] = True
    else:
        dic["refinement"] = False

    # Create the output folder
    if not os.path.exists(f"{dic['fol']}"):
        os.system(f"mkdir {dic['fol']}")

    # When a deck, only coarsened/refined/submodel/transformed files are generated
    if "DATA" in file:
        # if "/" in file:
        dic["deck"] = file.split("/")[-1][:-5]
        dic["pth"] = file[:-5]
        create_deck(dic)
        return

    # When a toml file, coarsened norne/drogon to use ERT for history matching

    # Open pycopm.utils.inputvalues to see the dic name abbreviations meaning
    process_input(dic, file)
    print(f"\npycopm is generating the input files for {dic['field']}, please wait.")

    for folder in ["preprocessing", "parameters", "jobs", "observations"]:
        if not os.path.exists(f"{dic['fol']}/{folder}"):
            os.system(f"mkdir {dic['fol']}/{folder}")

    # Read the data from the input model
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
            f" {dic['fol']}/preprocessing/include & wait"
        )
    else:
        os.system(
            f"cp -r {dic['pat']}/reference_simulation/{dic['field']}/INCLUDE"
            f" {dic['fol']}/preprocessing/INCLUDE & wait"
        )

    print(f"\nThe generated files have been written to {dic['fol']}")
    if dic["mode"] in ["single-run", "ert"]:
        print("\nRunning the simulations, please wait.")
        # Run Flow or selected ERT functionality
        simulations(dic)

        # Make some useful plots after the studies
        plotting(dic, time.monotonic() - start_time)


def load_parser():
    """Argument options"""
    parser = argparse.ArgumentParser(
        description="Main script to tailor the geological model and run "
        "simulations using OPM Flow. All flag values can be set for "
        "input decks, while only the flags -i and -o are valid for toml "
        "configuration files."
    )
    parser.add_argument(
        "-i",
        "--input",
        default="input.toml",
        help="The base name of the toml configuration file or the name of the deck, "
        "e.g., DROGON.DATA ('input.toml' by default).",
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
        help="OPM Flow path to executable (e.g., /home/pycopm/build/opm-simulators/bin/flow), "
        "or just 'flow' if this was installed via binaries or if the folder where flow is "
        "built has been added to your path ('flow' by default).",
    )
    parser.add_argument(
        "-m",
        "--mode",
        default="prep_deck",
        help="Execute a dry run of the input deck to generate the static properties ('prep'), "
        "generate only the modified files ('deck'), only exectute a dry run on the generated "
        "model ('dry'), 'prep_deck', 'deck_dry', or do all ('all') ('prep_deck' by "
        "default).",
    )
    parser.add_argument(
        "-v",
        "--vicinity",
        default="",
        help="The location to extract the sub model which can be assigned by "
        "region values, e.g., 'fipnum 2,4' extracts the cells with fipnums "
        "equal to 2 or 4, by a polygon given the xy locations in meters, e.g., "
        "'xypolygon [0,0] [30,0] [30,30] [0,0]', or by the name of the well "
        "and three different options for the neighbourhood: box, diamond, and diamondxy, where "
        "for box the i, j, and k interval around the connections are given, e.g., 'welln box "
        "[-1,1] [-2,2] [0,3]' results in a vicinity with 1 pm cell in the x direction, 2 pm "
        "cells in the y direction and only 3 cells in the k positive direction, while the diamond "
        "considers only the given number of cells around the well connections (e.g., 'welln "
        "diamond 2') and diamondxy it is restricted to the xy plane ('' by default).",
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
        help="Array of x-coarsening, e.g., if the grid has 6 cells in the x "
        "direction, then 0,2,0,2,0,2,0 would generate a coarsened model with 3 "
        "cells, while 0,2,2,2,2,2,0 would generate a coarsened model with 1 cell, "
        "i.e., 0 keeps the pilars while 2 removes them. As an alternative, the "
        "range of the cells to coarse can be given separate them by commas, e.g., "
        "1:3,5:6 generates a coarsened model with 3 cells where the cells with the "
        "first three and two last i indices are coarsened to one ('' by default).",
    )
    parser.add_argument(
        "-y",
        "--ycoar",
        default="",
        help="Array of y-coarsening, see the description for -x ('' by default).",
    )
    parser.add_argument(
        "-z",
        "--zcoar",
        default="",
        help="Array of z-coarsening, see the description for -x ('' by default).",
    )
    parser.add_argument(
        "-g",
        "--gridding",
        default="",
        help="Level of grid refinement in the x, y, and z dir ('' by default).",
    )
    parser.add_argument(
        "-rx",
        "--xref",
        default="",
        help="Array of x-refinement, e.g., if the grid has 6 cells in the x "
        "direction, then 0,1,0,2,0,4 would generate a refined model with 13 "
        "cells, while 0,0,0,1,0,0 would generate a refined model with 7 cells "
        "('' by default).",
    )
    parser.add_argument(
        "-ry",
        "--yref",
        default="",
        help="Array of y-refinement, see the description for -rx ('' by default).",
    )
    parser.add_argument(
        "-rz",
        "--zref",
        default="",
        help="Array of z-refinement, see the description for -rx ('' by default).",
    )
    parser.add_argument(
        "-a",
        "--how",
        default="mode",
        help="In coarsening, use 'min', 'max', or 'mode' to scale the actnum, e.g., min "
        "makes the new coarser cell inactive if at least one cell is inactive, while "
        "max makes it active it at least one cell is active ('mode' by default).",
    )
    parser.add_argument(
        "-n",
        "--nhow",
        default="mode",
        help="In coarsening, use 'min', 'max', or 'mode' to scale endnum, eqlnum, fipnum, "
        "fluxnum, imbnum, miscnum, multnum, opernum, pvtnum, rocknum, and satnum ('mode' "
        "by default).",
    )
    parser.add_argument(
        "-s",
        "--show",
        default="",
        help="In coarsening, use 'min', 'max', 'mean', or 'pvmean' to scale permx, permy, "
        "permz, poro, swatinit, disperc, thconr, and all mult(-)xyz ('' by default, i.e., "
        "using the arithmetic average for permx/permy, harmonic average for permz, volume "
        "weighted mean for mult(-)xyz, and the pore volume weighted ('pvmean') mean for "
        "the rest).",
    )
    parser.add_argument(
        "-p",
        "--pvcorr",
        default=0,
        help="In coarsening, set to '1' to add the removed pore volume to the closest coarser "
        "cells, while in submodels '1' adds the porv from outside on the boundary of the "
        "submodel, '2' adds the corner regions (e.g., below the mini and minj from the input "
        "model) to the corners in the submodel, '3' distributes the porv uniformly along the "
        "boundary, and '4' distributes it on the whole submodel ('0' by default, i.e., no "
        "porv correction).",
    )
    parser.add_argument(
        "-q",
        "--fipcorr",
        default=0,
        help="Adjust the pv to the initial FGIP and FOIP from the input deck; use this option "
        "only for systems with initial oil, gas, and water, e.g., norne or drogon, but "
        "no in Smeaheia ('0' by default, '1' to enable).",
    )
    parser.add_argument(
        "-t",
        "--trans",
        default=0,
        help="In coarsening, write and use upscaled transmissibilities by ('1') armonic "
        "averaging and summing the transmissibilities in the corresponding coarsening direction "
        "and ('2') scaling the face transmissibily on the coarse faces ('0' by default, i.e., "
        "transmissibilities are not used).",
    )
    parser.add_argument(
        "-r",
        "--remove",
        default="2",
        help="Remove CONFACT and KH from COMPDAT (1) and also remove PEQVR (2) (ITEM 13, the "
        "last entry) to compute the well transmisibility connections internally in OPM Flow "
        "using the grid properties ('2' by default; set to '0' to not remove).",
    )
    parser.add_argument(
        "-j",
        "--jump",
        default="",
        help="In coarsening, tuning parameter to avoid creation of neighbouring connections "
        "in the coarsened model where there are discontinuities between cells along "
        "the z direction, e.g., around faults ('' by default, i.e., nothing "
        "corrected; if need it, try with values of the order of 1).",
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
        help="Added text before each generated .INC ('PYCOPM_' by default, i.e., the modified "
        "porv is saved in PYCOPM_PORV.INC; set to '' to generate PORV.INC, PERMX.INC, etc).",
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
        help="Given i,j,k indices in the input model, return the modified i,j,k corresponding "
        "positions ('' by default; if not empty, e.g., '1,2,3', then "
        "there will not be generation of modified files, only the i,j,k mapped indices in the "
        "terminal).",
    )
    parser.add_argument(
        "-d",
        "--displace",
        default="",
        help="Options to transform the x,y,z coordinates: 'translate [10,-5,4]' adds the values "
        "in meters to the coordinates, 'scale [1,2,3]' multiplies the coordinates by the given "
        "values respectively, and 'rotatexy 45' applies a rotation in degrees in the xy plane "
        "(rotatexz and rotateyz applies a rotation around the y and x axis respectively) "
        "('' by default).",
    )
    parser.add_argument(
        "-explicit",
        "--explicit",
        default=0,
        help="Set to 1 to explicitly write the cell values in the SOLUTION section in the "
        "deck ('0' by default).",
    )
    parser.add_argument(
        "-warnings",
        "--warnings",
        default=0,
        help="Set to 1 to show Python warnings ('0' by default).",
    )
    return vars(parser.parse_known_args()[0])


def check_cmdargs(cmdargs):
    """
    Check for invalid combinations of command arguments

    Args:
        cmdargs (dict): Command flags

    Returns:
        None

    """
    if not (cmdargs["input"].strip()).endswith((".DATA", ".toml")):
        print(
            f"\nInvalid extension for input file '-i {cmdargs['input'].strip()}', "
            "valid extensions are .DATA or .toml\n"
        )
        sys.exit()
    if (cmdargs["input"].strip()).endswith(".DATA"):
        if (
            subprocess.call(
                cmdargs["flow"].strip(),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
            != 1
        ):
            print(
                f"\nThe OPM flow executable '-f {cmdargs['flow'].strip()}' is not found, "
                f"try to install it following the information in the documentation.\n"
            )
            sys.exit()
        for option, flag in zip(["how", "nhow"], ["-a", "-n"]):
            if cmdargs[option].strip() not in ["min", "max", "mode"]:
                print(
                    f"\nInvalid option for '{flag} {cmdargs['option'].strip()}', "
                    f"valid options are 'min', 'max', or 'mode'.\n"
                )
                sys.exit()
        if cmdargs["show"].strip():
            if cmdargs["show"].strip() not in ["min", "max", "mean", "pvmean"]:
                print(
                    f"\nInvalid option for '-s {cmdargs['show'].strip()}', "
                    f"valid options are 'min', 'max', 'mean', and 'pvmean'.\n"
                )
                sys.exit()
        if cmdargs["mode"].strip() not in [
            "prep",
            "deck",
            "dry",
            "prep_deck",
            "deck_dry",
            "all",
        ]:
            print(
                f"\nInvalid option for '-m {cmdargs['mode'].strip()}', "
                "valid options are 'prep', 'deck', 'dry', 'prep_deck', "
                "'deck_dry', and 'all'.\n"
            )
            sys.exit()
        if cmdargs["vicinity"].strip() and cmdargs["displace"].strip():
            print("\nInvalid combination, either set '-v' or '-d'.\n")
            sys.exit()
        if cmdargs["vicinity"].strip() and cmdargs["gridding"].strip():
            print("\nInvalid combination, either set '-v' or '-g'.\n")
            sys.exit()
        if cmdargs["displace"].strip() and cmdargs["gridding"].strip():
            print("\nInvalid combination, either set '-d' or '-g'.\n")
            sys.exit()


def main():
    """Main function"""
    pycopm()
