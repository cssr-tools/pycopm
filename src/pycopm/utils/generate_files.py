# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,R0801,E1102

"""
Create modified (coarser, finner, submodels, transformations) OPM files.
"""

import os
import csv
import sys
import subprocess
import numpy as np
from alive_progress import alive_bar
from opm.io.ecl import EclFile as OpmFile
from opm.io.ecl import EGrid as OpmGrid
from pycopm.utils.parser_deck import process_the_deck
from pycopm.utils.mapping_methods import (
    add_pv_bc,
    chop_grid,
    coarsening_dir,
    handle_pv,
    handle_cp_grid,
    handle_refinement,
    handle_clusters,
    handle_vicinity,
    map_ijk,
    map_properties,
    map_vicinity,
    refine_grid,
    transform_grid,
)


def create_deck(dic):
    """
    Main script to call the diffeent methods to generate the opm files

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    if dic["ijk"]:
        dic["ijk"] = [int(val) for val in dic["ijk"].split(",")]
        dic["mode"] = "deck"
    if not dic["write"]:
        dic["write"] = dic["deck"] + "_PYCOPM"
    dic["flags"] = (
        "--parsing-strictness=low --check-satfunc-consistency=false --enable-dry-run=true "
        "--output-mode=none"
    )
    dic["flags1"] = (
        "--parsing-strictness=low --check-satfunc-consistency=false --output-mode=none "
        "--solver-max-restarts=20 --solver-continue-on-convergence-failure=true "
        f"--output-dir={dic['fol']}"
    )
    types = [".INIT", ".EGRID"]
    if dic["mode"] in ["prep", "prep_deck", "all"]:
        if dic["explicit"]:
            types += [".UNRST"]
            dic["lol"] = []
            with open(dic["pth"] + ".DATA", "r", encoding="utf8") as file:
                for row in csv.reader(file):
                    nrwo = str(row)[2:-2].strip()
                    if nrwo == "SCHEDULE":
                        dic["lol"].append(nrwo)
                        dic["lol"].append("RPTRST\n'BASIC=2'/\n")
                        dic["lol"].append("TSTEP\n1*0.0001/\n")
                        break
                    dic["lol"].append(nrwo)
            with open(
                dic["deck"] + "_PREP_PYCOPM_DRYRUN.DATA",
                "w",
                encoding="utf8",
            ) as file:
                for row in dic["lol"]:
                    file.write(row + "\n")
            print(
                f"\nTemporal {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA from {dic['pth']}.DATA for"
                " the initial run to generate the grid (.EGRID), static (.INIT), and initial"
                " (.UNRST) properties\n"
            )
            os.system(
                f"{dic['flow']} {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA --output-mode=none "
                f"--parsing-strictness=low --enable-opm-rst-file=1 --output-dir={dic['fol']}"
            )
            os.system(f"rm {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA")
            os.system(f"cp {dic['pth']}.DATA {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA")
            print(
                f"\nCloning {dic['pth']}.DATA to {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA \n"
            )
        else:
            os.system(f"cp {dic['pth']}.DATA {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA")
            print(
                f"\nCloning {dic['pth']}.DATA to {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA for"
                " the initial dry run to generate the grid (.EGRID) and static"
                " (.INIT) properties\n"
            )
            os.system(
                f"{dic['flow']} {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA {dic['flags']} "
                f"--output-dir={dic['fol']}"
            )
        if dic["fol"] != os.path.abspath("."):
            os.system(f"mv {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA " + f"{dic['fol']}")
        for name in types:
            files = f"{dic['fol']}/{dic['deck']}_PREP_PYCOPM_DRYRUN" + name
            if not os.path.isfile(files):
                if name == ".INIT":
                    print(
                        f"\nThe {files} is not found, try adding the keyword INIT in"
                        f" the GRID section in the original deck {dic['deck']}.DATA\n"
                    )
                elif name == ".INIT":
                    print(
                        f"\nThe {files} is not found, try removing the keyword GRIDFILE in"
                        f" the GRID section in the original deck {dic['deck']}.DATA\n"
                    )
                else:
                    print(
                        f"\nThe {files} is not found, check the input deck {dic['deck']}"
                        f".DATA\n"
                    )
                sys.exit()
        print(
            f"\nThe initial/dry run of {dic['deck']}.DATA succeeded (see {dic['fol']}/)"
        )
    if dic["mode"] in ["prep_deck", "deck", "deck_dry", "all"]:
        coarsening_dir(dic)
        dic["deckn"] = dic["deck"]
        dic["deck"] = f"{dic['fol']}/{dic['deck']}_PREP_PYCOPM_DRYRUN"
        for name in types:
            files = dic["deck"] + name
            if not os.path.isfile(files):
                print(
                    f"\nThe {files} is not found, try running pycopm with -m prep_deck "
                    "and without -ijk"
                )
                sys.exit()
        dic["field"] = "generic"
        dic["props"] = ["permx", "permy", "permz", "poro"]
        dic["base"] = dic["props"] + ["grid"]
        for name in ["regions", "grids", "rptrst", "mults", "special", "reftocoa"]:
            dic[name] = []
        dic["fip"] = ""
        dic["nrptsrt"] = 0
        dic["nrptsrtc"] = 0
        dic["hasnnc"], dic["coarsening"] = False, False
        if dic["refinement"]:
            print("\nInitializing pycopm to generate the refinned files, please wait.")
        elif dic["vicinity"]:
            print("\nInitializing pycopm to generate the submodel files, please wait.")
        elif dic["transform"]:
            print(
                "\nInitializing pycopm to generate the transformed files, please wait."
            )
            dic["rcijk"] = np.array([0, 0, 0])
            dic["refinement"] = True
        elif not dic["ijk"]:
            dic["coarsening"] = True
            print("\nInitializing pycopm to generate the coarsened files, please wait.")
        initialize_variables(dic)
        dic["tc"] = dic["xn"] * dic["yn"] * dic["zn"]
        dic["con"] = np.array([0 for _ in range(dic["tc"])])
        if dic["trans"] > 0:
            for name in ["tranx", "trany", "tranz"]:
                dic["props"] += [name]
        dic["actind"] = dic["porv"] > 0
        if dic["refinement"]:
            handle_refinement(dic)
        elif dic["vicinity"]:
            handle_vicinity(dic)
        else:
            handle_clusters(dic)
            for name in dic["props"] + dic["regions"] + dic["grids"] + dic["rptrst"]:
                dic[name] = 1.0 * np.ones(dic["tc"]) * np.nan
        map_ijk(dic)
        if dic["ijk"]:
            print(
                dic["ic"][dic["ijk"][0]],
                dic["jc"][dic["ijk"][1]],
                dic["kc"][dic["ijk"][2]],
            )
            sys.exit()
        actnum = np.array([0 for _ in range(dic["tc"])])
        for i in ["x", "y", "z"]:
            dic[f"d_{i}"] = np.array([np.nan for _ in range(dic["tc"])])
            dic[f"d_a{i}"] = np.array([np.nan for _ in range(dic["tc"])])
        v_c = np.array([np.nan for _ in range(dic["tc"])])
        z_t = np.array([np.nan for _ in range(dic["tc"])])
        z_b = np.array([np.nan for _ in range(dic["tc"])])
        z_b_t = np.array([np.nan for _ in range(dic["tc"])])
        print("Processing the mappings")
        if dic["refinement"]:
            names = (
                dic["props"] + dic["regions"] + dic["grids"] + dic["rptrst"] + ["porv"]
            )
            with alive_bar(len(names)) as bar_animation:
                for name in names:
                    bar_animation()
                    dic[name] = np.zeros(dic["tc"])
                    if name == "porv":
                        dic[name] = np.divide(
                            np.array(dic["ini"][name.upper()]), dic["nc"]
                        )
                    elif name in dic["rptrst"]:
                        dic[name][dic["actind"]] = dic["rst"][name.upper(), 0]
                    else:
                        dic[name][dic["actind"]] = dic["ini"][name.upper()]
                    dic[f"{name}_c"] = [""] * (dic["nx"] * dic["ny"] * dic["nz"])
                    n = 0
                    for k in range(dic["zn"]):
                        for _ in range(dic["Z"][k] + 1):
                            for j in range(dic["yn"]):
                                for _ in range(dic["Y"][j] + 1):
                                    for i in range(dic["xn"]):
                                        ind = (
                                            i
                                            + j * dic["xn"]
                                            + k * dic["xn"] * dic["yn"]
                                        )
                                        for _ in range(dic["X"][i] + 1):
                                            dic[f"{name}_c"][n] = (
                                                f"{int(dic[name][ind])}"
                                                if "num" in name
                                                else f"{dic[name][ind]:E}"
                                            )
                                            n += 1
            dic["actnum_c"] = ["1" if float(val) > 0 else "0" for val in dic["porv_c"]]
        elif dic["vicinity"]:
            map_vicinity(dic)
        else:
            zti = [0, 1, 2, 3]
            zbi = [4, 5, 6, 7]
            actnum = 1 * (dic["porv"] > 0)
            v_c = np.array(dic["grid"].cellvolumes())
            for name in dic["props"] + dic["regions"] + dic["grids"]:
                dic[name][dic["actind"]] = dic["ini"][name.upper()]
            for name in dic["rptrst"]:
                dic[name][dic["actind"]] = dic["rst"][name.upper(), 0]
            with alive_bar(dic["tc"]) as bar_animation:
                for k in range(dic["zn"]):
                    for j in range(dic["yn"]):
                        for i in range(dic["xn"]):
                            bar_animation()
                            dic["reftocoa"].append(
                                dic["ic"][i + 1]
                                + (dic["jc"][j + 1] - 1) * dic["nx"]
                                + (dic["kc"][k + 1] - 1) * dic["nx"] * dic["ny"]
                            )
                            ind = i + j * dic["xn"] + k * dic["xn"] * dic["yn"]
                            cxyz = dic["grid"].xyz_from_ijk(i, j, k)
                            x_0, y_0, z_0 = 0.0, 0.0, 0.0
                            x_1, y_1 = 0.0, 0.0
                            for m, o, p in zip(range(4), [0, 0, 1, 1], [0, 1, 0, 1]):
                                x_0 += abs(cxyz[0][1 + 2 * m] - cxyz[0][2 * m]) / 4.0
                                x_1 += abs(cxyz[1][1 + 2 * m] - cxyz[1][2 * m]) / 4.0
                                y_0 += (
                                    abs(cxyz[0][p + o * 4 + 2] - cxyz[0][p + o * 4])
                                    / 4.0
                                )
                                y_1 += (
                                    abs(cxyz[1][p + o * 4 + 2] - cxyz[1][p + o * 4])
                                    / 4.0
                                )
                                z_0 += abs(cxyz[2][m + 4] - cxyz[2][m]) / 4.0
                            dic["d_x"][ind] = (x_0**2 + x_1**2) ** 0.5
                            dic["d_y"][ind] = (y_0**2 + y_1**2) ** 0.5
                            dic["d_z"][ind] = z_0
                            z_t[ind] = min(cxyz[2][i] for i in zti)
                            z_b[ind] = max(cxyz[2][i] for i in zti)
                            tmp = max(cxyz[2][i] for i in zbi)
                            z_b_t[ind] = tmp - z_t[ind]
            dic["d_ax"][dic["actind"]] = dic["d_x"][dic["actind"]]
            dic["d_ay"][dic["actind"]] = dic["d_y"][dic["actind"]]
            dic["d_az"][dic["actind"]] = dic["d_z"][dic["actind"]]
            if dic["show"] == "pvmean":
                for name in dic["props"] + dic["rptrst"]:
                    dic[name][dic["actind"]] *= dic["porv"][dic["actind"]]
            elif not dic["show"]:
                dic["permx"][dic["actind"]] *= dic["d_z"][dic["actind"]]
                dic["permy"][dic["actind"]] *= dic["d_z"][dic["actind"]]
                dic["permz"][dic["actind"]] = [
                    d_z / k_z if k_z > 0 else np.nan
                    for d_z, k_z in zip(
                        dic["d_z"][dic["actind"]], dic["permz"][dic["actind"]]
                    )
                ]
                dic["poro"][dic["actind"]] *= dic["porv"][dic["actind"]]
                if "swatinit" in dic["props"]:
                    dic["swatinit"][dic["actind"]] *= dic["porv"][dic["actind"]]
                for name in ["disperc", "thconr"]:
                    if name in dic["grids"]:
                        dic[name][dic["actind"]] *= dic["porv"][dic["actind"]]
                for name in dic["mults"]:
                    dic[name][dic["actind"]] *= v_c[dic["actind"]]
                if len(dic["coardir"]) == 1 and dic["trans"] == 1:
                    drc = dic["coardir"][0]
                    dic[f"tran{drc}"][dic["actind"]] = [
                        1.0 / val if val > 0 else np.nan
                        for val in dic[f"tran{drc}"][dic["actind"]]
                    ]
                for name in dic["rptrst"]:
                    dic[name][dic["actind"]] *= dic["porv"][dic["actind"]]
        process_the_deck(dic)
        if dic["transform"]:
            transform_grid(dic)
        elif dic["refinement"]:
            refine_grid(dic)
        elif dic["vicinity"]:
            chop_grid(dic)
            add_pv_bc(dic)
        else:
            clusmin, clusmax, rmv = map_properties(dic, actnum, z_t, z_b, z_b_t, v_c)
            if dic["pvcorr"] == 1:
                handle_pv(dic, clusmin, clusmax, rmv)
            handle_cp_grid(dic)
        write_grid(dic)
        write_props(dic)
        with open(
            f"{dic['fol']}/{dic['write']}.DATA",
            "w",
            encoding="utf8",
        ) as file:
            for row in dic["lol"]:
                file.write(row + "\n")
        if dic["fipcorr"] == 1:
            thr = 1e-1
            with open(
                f"{dic['fol']}/{dic['write']}_1STEP.DATA",
                "w",
                encoding="utf8",
            ) as file:
                for row in dic["lolc"]:
                    file.write(row + "\n")
            with open(
                f"{dic['fol']}/{dic['write']}_CORR.DATA",
                "w",
                encoding="utf8",
            ) as file:
                for row in dic["deckcorr"]:
                    file.write(row + "\n")
            print(
                f"\nRunning {dic['fol']}/{dic['write']}_1STEP.DATA and "
                f"{dic['fol']}/{dic['write']}_CORR.DATA to correct the pore volume\n"
            )
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_CORR.DATA {dic['flags1']}"
            )
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_1STEP.DATA {dic['flags1']}"
            )
            ref = OpmFile(f"{dic['fol']}/{dic['write']}_1STEP.UNRST")
            cor = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.UNRST")
            cori = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.INIT")
            ref_fipg = np.array(ref["FIPGAS", 0])
            ref_fipo = np.array(ref["FIPOIL", 0])
            cor_pv = np.array(cori["PORV"])
            cor_fipg = np.array(cor["FIPGAS", 0])
            cor_fipo = np.array(cor["FIPOIL", 0])
            cor_pa = cor_pv[cor_pv > 0]
            fact = np.sum(ref_fipo) / np.sum(cor_fipo) - 1
            cor_pa[cor_fipo <= thr] -= (
                fact * np.sum(cor_pa[cor_fipo > thr]) / len(cor_pa[cor_fipo <= thr])
            )
            cor_pa[cor_fipo > thr] *= 1 + fact
            cor_pv[cor_pv > 0] = cor_pa
            cor_pv[np.isnan(cor_pv)] = 0
            cor_pv = compact_format("".join(f"{val} " for val in cor_pv).split())
            with open(
                f"{dic['fol']}/{dic['label']}PORV.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("PORV\n")
                file.write("".join(cor_pv))
                file.write("/\n")
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_CORR.DATA {dic['flags1']}"
            )
            cor = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.UNRST")
            cori = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.INIT")
            cor_pv = np.array(cori["PORV"])
            cor_fipg = np.array(cor["FIPGAS", 0])
            cor_fipo = np.array(cor["FIPOIL", 0])
            cor_sgas = np.array(cor["SGAS", 0])
            cor_pa = cor_pv[cor_pv > 0]
            fact = (np.sum(ref_fipg) - np.sum(cor_fipg)) / np.sum(
                cor_fipg[cor_sgas > thr]
            )
            cor_pa[cor_fipo <= thr] -= (
                fact * np.sum(cor_pa[cor_sgas > thr]) / len(cor_pa[cor_fipo <= thr])
            )
            cor_pa[cor_sgas > thr] *= 1 + fact
            cor_pv[cor_pv > 0] = cor_pa
            cor_pv[np.isnan(cor_pv)] = 0
            cor_pv = compact_format("".join(f"{val} " for val in cor_pv).split())
            with open(
                f"{dic['fol']}/{dic['label']}PORV.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("PORV\n")
                file.write("".join(cor_pv))
                file.write("/\n")
            print(
                f"\nRunning {dic['fol']}/{dic['write']}_CORR.DATA with the corrected "
                "pore volume\n"
            )
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_CORR.DATA {dic['flags1']}"
            )
        if dic["hasnnc"] > 0 and dic["coarsening"]:
            print("\nCall OPM Flow for a dry run of the generated model.\n")
            print("\nThis is needed for the nnctrans, please wait.\n")
            os.chdir(dic["fol"])
            os.system(f"{dic['flow']} {dic['fol']}/{dic['write']}.DATA {dic['flags']}")
            if (
                OpmFile(dic["write"] + ".EGRID").count("NNC1")
                or OpmFile(dic["deck"] + ".EGRID").count("NNC1")
            ) and dic["trans"] > 0:
                handle_nnc_trans(dic)
            else:
                print("\nNo nnctrans found.")
        print(
            f"\nThe generation of files succeeded, see {dic['fol']}/"
            f"{dic['write']}.DATA and {dic['fol']}/{dic['label']}*.INC\n"
        )

    if dic["mode"] in ["deck_dry", "dry", "all"]:
        print("\nCall OPM Flow for a dry run of the generated model.\n")
        os.chdir(dic["fol"])
        subprocess.run(
            [dic["flow"], f"{dic['write']}.DATA"] + dic["flags"].split(" "), check=False
        )
        # It seems there is a bug for dryruns in flow, commenting the following until fixing this
        # if prosc.returncode != 0:
        #     print(
        #         "\nThe dry run of the generated model "
        #         f"{dic['fol']}/{dic['write']}.DATA failed. Check the Flow output in the "
        #         "terminal for the error which might be possible to fix by correcting the "
        #         f"input deck {dic['pth']}.DATA or the generated deck; otherwise, please raise an "
        #         "issue at https://github.com/cssr-tools/pycopm/issues"
        #     )
        # else:
        #     print(
        #         "\nThe dry run of the generated model "
        #         f"{dic['fol']}/{dic['write']}.DATA succeeded.\n"
        #     )
        print(f"\nThe dryrun results have been written to {dic['fol']}/")


def bool_mult(dic, nrwo, mults):
    """
    Set to True if the keyword is found

    Args:
        dic (dict): Global dictionary\n
        nrwo (str): Entry of the deck\n
        mults (list): Name of MULT* keywords

    Returns:
        dic (dict): Modified global dictionary

    """
    keyword = nrwo.split()
    for name in mults:
        if nrwo == name.upper() or (len(keyword) > 1 and keyword[0] == name.upper()):
            dic[f"has{name}"] = True


def search_file(dic, path, mults):
    """
    Check the file for the keywords

    Args:
        dic (dict): Global dictionary\n
        path (str): Path to the file\n
        mults (list): Name of MULT* keywords

    Returns:
        dic (dict): Modified global dictionary

    """
    includes, include = [], False
    data = ".DATA" in path
    with open(path, "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            if include:
                inc = os.path.join(
                    os.getcwd(), nrwo.split("/", maxsplit=1)[0].strip().strip("\"'")
                )
                if os.path.exists(inc):
                    includes.append(inc)
                include = False
                continue
            bool_mult(dic, nrwo, mults)
            if nrwo == "INCLUDE":
                include = True
            if data and nrwo == "MULTFLT":
                dic["maindeckmultflt"] = True
    return includes


def check_mult(dic, mults):
    """
    Check for MULT* to avoid writing them if only MULTFLT is used.
    We look at most for three levels of INCLUDE

    Args:
        dic (dict): Global dictionary\n
        mults (list): Name of MULT* keywords

    Returns:
        dic (dict): Modified global dictionary

    """
    for name in mults:
        dic[f"has{name}"] = False
    includes = search_file(dic, dic["deck"] + ".DATA", mults)
    includes1, includes2 = [], []
    for include in includes:
        includes1.extend(search_file(dic, include, mults))
    for include in includes1:
        includes2.extend(search_file(dic, include, mults))
    for include in includes2:
        search_file(dic, include, mults)


def initialize_variables(dic):
    """
    Use opm to read the dry run

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    speciales = ["swatinit", "sowcr", "sogcr", "swcr", "sgu", "swl"]
    speciales += ["krwr", "krw", "krorw", "krorg", "kro", "krgr", "krg"]
    dic["ogrid"] = OpmFile(dic["deck"] + ".EGRID")
    if dic["ogrid"].count("NNC1") and dic["trans"] > 0:
        dic["hasnnc"] = True
    dic["grid"] = OpmGrid(dic["deck"] + ".EGRID")
    dic["ini"] = OpmFile(dic["deck"] + ".INIT")
    for name in speciales:
        if dic["ini"].count(name.upper()):
            dic["props"] += [name]
            dic["special"] += [name]
    mults = ["multx", "multx-", "multy", "multy-", "multz", "multz-"]
    dic["maindeckmultflt"] = False
    check_mult(dic, mults)
    for name in mults:
        if dic["ini"].count(name.upper()):
            tmp = np.array(dic["ini"][name.upper()])
            if 0 < np.sum(tmp != 1):
                if dic[f"has{name}"] or not dic["maindeckmultflt"]:
                    dic["props"] += [name]
                    dic["mults"] += [name]
    for name in ["multnum", "fluxnum"]:
        if dic["ini"].count(name.upper()):
            if (
                np.max(dic["ini"][name.upper()]) > 1
                or np.min(dic["ini"][name.upper()]) < 1
            ):
                dic["grids"] += [name]
    for name in ["thconr", "disperc"]:
        if dic["ini"].count(name.upper()):
            dic["grids"] += [name]
    for name in [
        "endnum",
        "eqlnum",
        "fipnum",
        "imbnum",
        "miscnum",
        "opernum",
        "pvtnum",
        "rocknum",
        "satnum",
    ]:
        if dic["ini"].count(name.upper()):
            if (
                np.max(dic["ini"][name.upper()]) > 1
                or np.min(dic["ini"][name.upper()]) < 1
            ):
                dic["regions"] += [name]
    dic["xn"] = dic["grid"].dimension[0]
    dic["yn"] = dic["grid"].dimension[1]
    dic["zn"] = dic["grid"].dimension[2]
    dic["porv"] = np.array(dic["ini"]["PORV"])
    if dic["explicit"]:
        dic["solution"] = []
        dic["rst"] = OpmFile(dic["deck"] + ".UNRST")
        for name in [
            "sgas",
            "soil",
            "swat",
            "rs",
            "rv",
            "rsw",
            "rvw",
            "pressure",
            "sbiof",
            "scalc",
            "smicr",
            "soxyg",
            "surea",
            "ssol",
            "spoly",
            "surf",
            "spoly",
            "saltp",
            "salt",
        ]:
            if dic["rst"].count(name.upper()):
                dic["rptrst"] += [name]
    dic["facpermz"] = -1.0
    for i, val in enumerate(dic["ini"]["PERMX"]):
        if val != 0:
            if dic["ini"]["PERMZ"][i] != 0:
                dic["facpermz"] = dic["ini"]["PERMZ"][i] / float(val)
                break


def handle_nnc_trans(dic):
    """
    Map the trans from the non-neighbouring connections

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    temp = OpmFile(dic["deck"] + ".EGRID")
    coa = OpmFile(dic["write"] + ".INIT")
    editnnc = OpmFile(dic["write"] + ".EGRID").count("NNC1")
    if editnnc:
        nncdeck, indel, withlines = [], [], False
        dic["coa_editnnc"] = []
        dic["nnct"] = [[[] for _ in range(dic["yn"])] for _ in range(dic["xn"])]
        with open(dic["write"] + ".DATA", "r", encoding=dic["encoding"]) as file:
            for row in csv.reader(file):
                nrwo = str(row)[2:-2].strip()
                nncdeck.append(nrwo)
                if withlines:
                    nncdeck.append("INCLUDE")
                    nncdeck.append(f"'{dic['label']}EDITNNC.INC' /\n")
                    withlines = False
                elif nrwo == "EDIT":
                    if not dic["lines"]:
                        nncdeck.append("INCLUDE")
                        nncdeck.append(f"'{dic['label']}EDITNNC.INC' /\n")
                    else:
                        withlines = True
        with open(
            f"{dic['fol']}/{dic['write']}.DATA",
            "w",
            encoding="utf8",
        ) as file:
            for row in nncdeck:
                file.write(row + "\n")
        coag = OpmFile(dic["write"] + ".EGRID")
        cnnc1 = np.array(coag["NNC1"])
        cnnc2 = np.array(coag["NNC2"])
        cnnct = np.array(coa["TRANNNC"])
        coag = OpmGrid(dic["write"] + ".EGRID")
    rnnc1 = np.array(temp["NNC1"])
    rnnc2 = np.array(temp["NNC2"])
    rnnct = np.array(dic["ini"]["TRANNNC"])
    coapv = np.array(coa["PORV"])
    dic["coa_tranx"] = np.zeros(len(coapv))
    dic["coa_trany"] = np.zeros(len(coapv))
    dic["coa_tranx"][coapv > 0] = np.array(coa["TRANX"])
    dic["coa_trany"][coapv > 0] = np.array(coa["TRANY"])
    for r1, r2, trn in zip(rnnc1, rnnc2, rnnct):
        rijk1 = dic["grid"].ijk_from_global_index(r1 - 1)
        rijk2 = dic["grid"].ijk_from_global_index(r2 - 1)
        if dic["kc"][rijk1[2] + 1] == dic["kc"][rijk2[2] + 1] and (
            rijk1[0] != rijk2[0] or rijk1[1] != rijk2[1]
        ):
            if rijk1[0] + 1 == rijk2[0]:
                ind = (
                    (dic["ic"][rijk1[0] + 1] - 1)
                    + (dic["jc"][rijk1[1] + 1] - 1) * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_tranx"][ind] += trn
            elif rijk1[1] + 1 == rijk2[1]:
                ind = (
                    (dic["ic"][rijk1[0] + 1] - 1)
                    + (dic["jc"][rijk1[1] + 1] - 1) * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_trany"][ind] += trn
            elif rijk1[0] == rijk2[0] + 1:
                ind = (
                    (dic["ic"][rijk2[0] + 1] - 1)
                    + (dic["jc"][rijk2[1] + 1] - 1) * dic["nx"]
                    + (dic["kc"][rijk2[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_tranx"][ind] += trn
            elif rijk1[1] == rijk2[1] + 1:
                ind = (
                    (dic["ic"][rijk2[0] + 1] - 1)
                    + (dic["jc"][rijk2[1] + 1] - 1) * dic["nx"]
                    + (dic["kc"][rijk2[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_trany"][ind] += trn
        elif editnnc:
            dic["nnct"][rijk1[0]][rijk1[1]].append([rijk1[2], rijk2[2], trn])
    if editnnc:
        print("Processing the transmissibilities")
        with alive_bar(len(cnnc1)) as bar_animation:
            for n, (n1, n2) in enumerate(zip(cnnc1, cnnc2)):
                bar_animation()
                ijk1 = coag.ijk_from_global_index(n1 - 1)
                ijk2 = coag.ijk_from_global_index(n2 - 1)
                fip1, fip2 = ijk1[2] + 1, ijk2[2] + 1
                rtran, found, indel = 0, 0, []
                if fip1 != fip2 and (ijk1[0] != ijk2[0] or ijk1[1] != ijk2[1]):
                    for i, val in enumerate(dic["nnct"][ijk1[0]][ijk1[1]]):
                        rfip1 = dic["kc"][val[0] + 1]
                        rfip2 = dic["kc"][val[1] + 1]
                        if fip1 == rfip1 and fip2 == rfip2:
                            rtran += val[2]
                            found = 1
                            indel.append(i)
                    for ind in indel[::-1]:
                        del dic["nnct"][ijk1[0]][ijk1[1]][ind]
                    if found == 1:
                        mult = rtran / cnnct[n]
                    else:
                        mult = 0
                    dic["coa_editnnc"].append(
                        f"{ijk1[0]+1} {ijk1[1]+1} {ijk1[2]+1} {ijk2[0]+1} "
                        f"{ijk2[1]+1} {ijk2[2]+1} {mult} /"
                    )
    cases = ["tranx", "trany"]
    if editnnc:
        cases += ["editnnc"]
    for name in cases:
        if name == "editnnc":
            dic[f"coa_{name}"] = [f"{val}\n" for val in dic[f"coa_{name}"]]
        else:
            dic[f"coa_{name}"] = [f"{val:E} " for val in dic[f"coa_{name}"]]
            dic[f"coa_{name}"] = compact_format("".join(dic[f"coa_{name}"]).split())
        dic[f"coa_{name}"].insert(0, name.upper() + "\n")
        dic[f"coa_{name}"].insert(
            0,
            "-- This file was generated by pycopm https://github.com/cssr-tools/pycopm\n",
        )
        dic[f"coa_{name}"].append("/\n")
        with open(
            f"{dic['label']}{name.upper()}.INC",
            "w",
            encoding="utf8",
        ) as file:
            file.write("".join(dic[f"coa_{name}"]))


def write_grid(dic):
    """
    Write the corner-point grid

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    dic["ntot"] = dic["nx"] * dic["ny"] * dic["nz"]
    grid, tmp = [], []
    grid.append(
        "-- This deck was generated by pycopm https://github.com/cssr-tools/pycopm\n"
    )
    grid.append("-- Copyright (C) 2024-2026 NORCE Research AS\n")
    grid.append("SPECGRID\n")
    grid.append(f"{dic['nx']} {dic['ny']} {dic['nz']} /\n")
    grid.append("COORD\n")
    for i in range(int(len(dic["cr"]) / 6)):
        for j in range(6):
            tmp.append(f"{dic['cr'][i*6+j]:E} ")
    grid += compact_format("".join(tmp).split())
    grid.append("/\n")
    grid.append("ZCORN\n")
    tmp = []
    for i in range(int(len(dic["zc"]) / 8)):
        for j in range(8):
            tmp.append(f"{dic['zc'][i*8+j]:E} ")
    grid += compact_format("".join(tmp).split())
    grid.append("/")
    if dic["field"] == "generic":
        grid.append("\nACTNUM\n")
        grid += compact_format(" ".join(list(map(str, dic["actnum_c"]))).split())
        grid.append("/\n")
        with open(f"{dic['fol']}/{dic['label']}GRID.INC", "w", encoding="utf8") as file:
            file.write("".join(grid))
    else:
        grid.append("\n")
        with open(
            f"{dic['fol']}/preprocessing/{dic['name']}_COARSER.GRDECL",
            "w",
            encoding="utf8",
        ) as file:
            file.write("".join(grid))


def write_props(dic):
    """
    Write the modified properties

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    names = dic["props"] + dic["regions"] + dic["grids"] + dic["rptrst"] + ["porv"]
    names = compact_perm(dic, names)
    if dic["vicinity"]:
        names += ["subtoglob"]
        fips = [f"{int(val)+1} " for val in dic["subm"]]
        fips = compact_format("".join(f"{3-int(val)} " for val in fips).split())
        with open(
            f"{dic['fol']}/{dic['deckn']}_FIPNUM_PYCOPM_SUBMODEL.INC",
            "w",
            encoding="utf8",
        ) as file:
            file.write("FIPNUM\n")
            file.write("".join(fips))
            file.write("/\n")
    elif dic["coarsening"]:
        oprs = [f"{int(val)} " for val in dic["reftocoa"]]
        oprs = compact_format("".join(f"{int(val)} " for val in oprs).split())
        with open(
            f"{dic['fol']}/{dic['deckn']}_OPERNUM_PYCOPM_REFTOCOA.INC",
            "w",
            encoding="utf8",
        ) as file:
            file.write("OPERNUM\n")
            file.write("".join(oprs))
            file.write("/\n")
    print("Writing the files")
    with alive_bar(len(names)) as bar_animation:
        for name in names:
            bar_animation()
            dic[f"{name}_c"] = compact_format(dic[f"{name}_c"])
            if "*" in dic[f"{name}_c"][0] and not (
                dic["trans"] > 0 and name in ["tranx", "trany"]
            ):
                if int(dic[f"{name}_c"][0].split("*")[0]) == dic["ntot"]:
                    whr = dic["lol"].index(f"'{dic['label']}{name.upper()}.INC' /\n")
                    del dic["lol"][whr]
                    del dic["lol"][whr - 1]
                    dic["lol"].insert(
                        whr - 1, f"{name.upper()}\n{dic[f'{name}_c'][0]}/\n"
                    )
                    continue
            if name == "subtoglob":
                dic[f"{name}_c"].insert(0, "OPERNUM\n")
            else:
                dic[f"{name}_c"].insert(0, f"{name.upper()}\n")
            dic[f"{name}_c"].insert(
                0,
                "-- This file was generated by pycopm https://github.com/cssr-tools/pycopm\n",
            )
            dic[f"{name}_c"].append("/\n")
            with open(
                f"{dic['fol']}/{dic['label']}{name.upper()}.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("".join(dic[f"{name}_c"]))


def compact_perm(dic, names):
    """
    Use COPY and MULTIPLY is PERMY and PERMZ can be generated from PERMX

    Args:
        dic (dict): Global dictionary\n
        names (list): Properties to write the .INC

    Returns:
        names (list): Modified properties to write the .INC

    """
    cpermy, cpermz = False, False
    if dic["permx_c"] == dic["permy_c"]:
        names.remove("permy")
        whr = dic["lol"].index(f"'{dic['label']}PERMY.INC' /\n")
        del dic["lol"][whr]
        del dic["lol"][whr]
        cpermy = True
    if dic["facpermz"] > 0:
        delpermz = True
        for permx, permz in zip(dic["permx_c"], dic["permz_c"]):
            if abs(float(permz) - dic["facpermz"] * float(permx)) > 1e-12:
                delpermz = False
                break
        if delpermz:
            names.remove("permz")
            whr = dic["lol"].index(f"'{dic['label']}PERMZ.INC' /\n")
            del dic["lol"][whr]
            del dic["lol"][whr]
            cpermz = True
    if cpermy and cpermz:
        text = "COPY\nPERMX PERMY /\nPERMX PERMZ /\n/\n"
        if abs(1 - dic["facpermz"]) > 1e-12:
            text += f"\nMULTIPLY\nPERMZ {dic['facpermz']:.4E} /\n/\n"
        dic["lol"].insert(whr - 1, text)
    elif cpermy:
        text = "COPY\nPERMX PERMY /\n/\n"
        dic["lol"].insert(whr - 1, text)
    elif cpermz:
        text = "COPY\nPERMX PERMZ /\n/"
        if abs(1 - dic["facpermz"]) > 1e-12:
            text += f"\nMULTIPLY\nPERMZ {dic['facpermz']:.4E} /\n/\n"
        dic["lol"].insert(whr - 1, text)
    return names


def compact_format(values):
    """
    Use the 'n*x' notation to write repited values to save storage

    Args:
        values (list): List with the variable values

    Returns:
        values (list): List with the compacted variable values

    """
    n, value0, tmp = 0, float(values[0]), []
    for value in values:
        if value0 != float(value) or len(values) == 1:
            if value0 == 0:
                tmp.append(f"{n}*0 " if n > 1 else "0 ")
            elif value0.is_integer():
                tmp.append(f"{n}*{int(value0)} " if n > 1 else f"{int(value0)} ")
            else:
                tmp.append(f"{n}*{value0} " if n > 1 else f"{value0} ")
            n = 1
            value0 = float(value)
        else:
            n += 1
    if value0 == float(values[-1]) and len(values) > 1:
        if value0 == 0:
            tmp.append(f"{n}*0 " if n > 1 else "0 ")
        elif value0.is_integer():
            tmp.append(f"{n}*{int(value0)} " if n > 1 else f"{int(value0)} ")
        else:
            tmp.append(f"{n}*{value0} " if n > 1 else f"{value0} ")
    return tmp
