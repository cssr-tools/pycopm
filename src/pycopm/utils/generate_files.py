# SPDX-FileCopyrightText: 2024 NORCE
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
from resdata.grid import Grid
from resdata.resfile import ResdataFile
from mako.template import Template
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

try:
    from opm.io.ecl import EclFile as OpmFile
    from opm.io.ecl import EGrid as OpmGrid
except ImportError:
    pass


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
    dic["flags"] = "--parsing-strictness=low --enable-dry-run=true --output-mode=none"
    dic["flags1"] = (
        f"--parsing-strictness=low --output-mode=none --output-dir={dic['fol']}"
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
        dic["regions"] = []
        dic["grids"] = []
        dic["rptrst"] = []
        dic["mults"] = []
        dic["special"] = []
        dic["fip"] = ""
        dic["nrptsrt"] = 0
        dic["nrptsrtc"] = 0
        dic["hasnnc"] = False
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
                    if dic["resdata"]:
                        if name == "porv":
                            dic[name] = np.divide(
                                np.array(dic["ini"].iget_kw(name.upper())[0]), dic["nc"]
                            )
                        elif name in dic["rptrst"]:
                            dic[name][dic["actind"]] = dic["rst"].iget_kw(name.upper())[
                                0
                            ]
                        else:
                            dic[name][dic["actind"]] = dic["ini"].iget_kw(name.upper())[
                                0
                            ]
                    else:
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
                                            dic[f"{name}_c"][n] = str(
                                                int(dic[name][ind])
                                                if "num" in name
                                                else dic[name][ind]
                                            )
                                            n += 1
            dic["actnum_c"] = ["1" if float(val) > 0 else "0" for val in dic["porv_c"]]
        elif dic["vicinity"]:
            map_vicinity(dic)
        else:
            if not dic["resdata"]:
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
                                ind = i + j * dic["xn"] + k * dic["xn"] * dic["yn"]
                                cxyz = dic["grid"].xyz_from_ijk(i, j, k)
                                x_0, y_0, z_0 = 0.0, 0.0, 0.0
                                x_1, y_1 = 0.0, 0.0
                                for m, o, p in zip(
                                    range(4), [0, 0, 1, 1], [0, 1, 0, 1]
                                ):
                                    x_0 += (
                                        abs(cxyz[0][1 + 2 * m] - cxyz[0][2 * m]) / 4.0
                                    )
                                    x_1 += (
                                        abs(cxyz[1][1 + 2 * m] - cxyz[1][2 * m]) / 4.0
                                    )
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
            else:
                zti = [2, 5, 8, 11]
                zbi = [14, 17, 20, 23]
                cxyz = dic["grid"].export_corners(dic["grid"].export_index())
                for name in dic["props"] + dic["regions"] + dic["grids"]:
                    dic[name][dic["actind"]] = dic["ini"].iget_kw(name.upper())[0]
                for name in dic["rptrst"]:
                    dic[name][dic["actind"]] = dic["rst"].iget_kw(name.upper())[0]
                with alive_bar(dic["tc"]) as bar_animation:
                    for cell in dic["grid"].cells():
                        bar_animation()
                        dic["d_x"][cell.global_index] = dic["grid"].get_cell_dims(
                            ijk=(cell.i, cell.j, cell.k)
                        )[0]
                        dic["d_y"][cell.global_index] = dic["grid"].get_cell_dims(
                            ijk=(cell.i, cell.j, cell.k)
                        )[1]
                        actnum[cell.global_index] = cell.active
                        z_t[cell.global_index] = min(
                            cxyz[cell.global_index][i] for i in zti
                        )
                        z_b[cell.global_index] = max(
                            cxyz[cell.global_index][i] for i in zti
                        )
                        tmp = max(cxyz[cell.global_index][i] for i in zbi)
                        z_b_t[cell.global_index] = tmp - z_t[cell.global_index]
                        dic["d_z"][cell.global_index] = dic["grid"].cell_dz(
                            ijk=(cell.i, cell.j, cell.k)
                        )
                        v_c[cell.global_index] = dic["grid"].cell_volume(
                            ijk=(cell.i, cell.j, cell.k)
                        )
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
            if dic["pvcorr"] > 0:
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
                f"{dic['fol']}/{dic['write']}_2DAYS.DATA",
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
                f"\nRunning {dic['fol']}/{dic['write']}_2DAYS.DATA and "
                f"{dic['fol']}/{dic['write']}_CORR.DATA to correct the pore volume\n"
            )
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_CORR.DATA {dic['flags1']}"
            )
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_2DAYS.DATA {dic['flags1']}"
            )
            if dic["resdata"]:
                ref = ResdataFile(f"{dic['fol']}/{dic['write']}_2DAYS.UNRST")
                cor = ResdataFile(f"{dic['fol']}/{dic['write']}_CORR.UNRST")
                cori = ResdataFile(f"{dic['fol']}/{dic['write']}_CORR.INIT")
                ref_fipg = np.array(ref.iget_kw("FIPGAS")[0])
                ref_fipo = np.array(ref.iget_kw("FIPOIL")[0])
                cor_pv = np.array(cori.iget_kw("PORV")[0])
                cor_fipg = np.array(cor.iget_kw("FIPGAS")[0])
                cor_fipo = np.array(cor.iget_kw("FIPOIL")[0])
            else:
                ref = OpmFile(f"{dic['fol']}/{dic['write']}_2DAYS.UNRST")
                cor = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.UNRST")
                cori = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.INIT")
                ref_fipg = np.array(ref["FIPGAS", 0])
                ref_fipo = np.array(ref["FIPOIL", 0])
                cor_pv = np.array(cori["PORV"])
                cor_fipg = np.array(cor["FIPGAS", 0])
                cor_fipo = np.array(cor["FIPOIL", 0])
            cor_pa = cor_pv[cor_pv > 0]
            fact = sum(ref_fipo) / sum(cor_fipo) - 1
            cor_pa[cor_fipo <= thr] -= (
                fact * sum(cor_pa[cor_fipo > thr]) / len(cor_pa[cor_fipo <= thr])
            )
            cor_pa[cor_fipo > thr] *= 1 + fact
            cor_pv[cor_pv > 0] = cor_pa
            with open(
                f"{dic['fol']}/{dic['label']}PORV.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("PORV\n")
                file.write("\n".join(f"{val}" for val in cor_pv))
                file.write("\n/")
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_CORR.DATA {dic['flags1']}"
            )
            if dic["resdata"]:
                cor = ResdataFile(f"{dic['fol']}/{dic['write']}_CORR.UNRST")
                cori = ResdataFile(f"{dic['fol']}/{dic['write']}_CORR.INIT")
                cor_pv = np.array(cori.iget_kw("PORV")[0])
                cor_fipg = np.array(cor.iget_kw("FIPGAS")[0])
                cor_fipo = np.array(cor.iget_kw("FIPOIL")[0])
                cor_sgas = np.array(cor.iget_kw("SGAS")[0])
            else:
                cor = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.UNRST")
                cori = OpmFile(f"{dic['fol']}/{dic['write']}_CORR.INIT")
                cor_pv = np.array(cori["PORV"])
                cor_fipg = np.array(cor["FIPGAS", 0])
                cor_fipo = np.array(cor["FIPOIL", 0])
                cor_sgas = np.array(cor["SGAS", 0])
            cor_pa = cor_pv[cor_pv > 0]
            fact = (sum(ref_fipg) - sum(cor_fipg)) / sum(cor_fipg[cor_sgas > thr])
            cor_pa[cor_fipo <= thr] -= (
                fact * sum(cor_pa[cor_sgas > thr]) / len(cor_pa[cor_fipo <= thr])
            )
            cor_pa[cor_sgas > thr] *= 1 + fact
            cor_pv[cor_pv > 0] = cor_pa
            with open(
                f"{dic['fol']}/{dic['label']}PORV.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("PORV\n")
                file.write("\n".join(f"{val}" for val in cor_pv))
                file.write("\n/")
            print(
                f"\nRunning {dic['fol']}/{dic['write']}_CORR.DATA with the corrected "
                "pore volume\n"
            )
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_CORR.DATA {dic['flags1']}"
            )
        if dic["hasnnc"] > 0:
            print("\nCall OPM Flow for a dry run of the generated model.\n")
            print("\nThis is needed for the nnctrans, please wait.\n")
            os.chdir(dic["fol"])
            os.system(f"{dic['flow']} {dic['fol']}/{dic['write']}.DATA {dic['flags']}")
            handle_nnc_trans(dic)
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
        # prosc = subprocess.run(
        #     [dic["flow"], f"{dic['write']}.DATA"] + dic["flags"].split(" "), check=False
        # )
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


def initialize_variables(dic):
    """
    Use resdata or opm to read the dry run

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    if dic["resdata"]:
        temp = ResdataFile(dic["deck"] + ".EGRID")
        if temp.has_kw("NNC1") and dic["trans"] > 0:
            dic["hasnnc"] = True
        dic["grid"] = Grid(dic["deck"] + ".EGRID")
        dic["ini"] = ResdataFile(dic["deck"] + ".INIT")
        if dic["ini"].has_kw("SWATINIT"):
            dic["props"] += ["swatinit"]
            dic["special"] += ["swatinit"]
        for name in ["multx", "multx-", "multy", "multy-", "multz", "multz-"]:
            if dic["ini"].has_kw(name.upper()):
                tmp = np.array(dic["ini"].iget_kw(name.upper())[0])
                if 0 < sum(tmp != 1):
                    dic["props"] += [name]
                    dic["mults"] += [name]
        for name in ["multnum", "fluxnum"]:
            if dic["ini"].has_kw(name.upper()):
                if max(dic["ini"].iget_kw(name.upper())[0]) > 1:
                    dic["grids"] += [name]
        for name in ["thconr", "disperc"]:
            if dic["ini"].has_kw(name.upper()):
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
            if dic["ini"].has_kw(name.upper()):
                if (
                    max(dic["ini"].iget_kw(name.upper())[0]) > 1
                    or min(dic["ini"].iget_kw(name.upper())[0]) < 1
                ):
                    dic["regions"] += [name]
        dic["xn"] = dic["grid"].nx
        dic["yn"] = dic["grid"].ny
        dic["zn"] = dic["grid"].nz
        dic["porv"] = np.array(dic["ini"].iget_kw("PORV")[0])
        if dic["explicit"]:
            dic["solution"] = []
            dic["rst"] = ResdataFile(dic["deck"] + ".UNRST")
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
                if dic["rst"].has_kw(name.upper()):
                    dic["rptrst"] += [name]
    else:
        dic["ogrid"] = OpmFile(dic["deck"] + ".EGRID")
        if dic["ogrid"].count("NNC1") and dic["trans"] > 0:
            dic["hasnnc"] = True
        dic["grid"] = OpmGrid(dic["deck"] + ".EGRID")
        dic["ini"] = OpmFile(dic["deck"] + ".INIT")
        if dic["ini"].count("SWATINIT"):
            dic["props"] += ["swatinit"]
            dic["special"] += ["swatinit"]
        for name in ["multx", "multx-", "multy", "multy-", "multz", "multz-"]:
            if dic["ini"].count(name.upper()):
                tmp = np.array(dic["ini"][name.upper()])
                if 0 < sum(tmp != 1):
                    dic["props"] += [name]
                    dic["mults"] += [name]
        for name in ["multnum", "fluxnum"]:
            if dic["ini"].count(name.upper()):
                if max(dic["ini"][name.upper()]) > 1:
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
                    max(dic["ini"][name.upper()]) > 1
                    or min(dic["ini"][name.upper()]) < 1
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


def handle_nnc_trans(dic):
    """
    Map the trans from the non-neighbouring connections

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    nncdeck = []
    with open(dic["write"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            nncdeck.append(nrwo)
            if nrwo == "EDIT":
                nncdeck.append("INCLUDE")
                nncdeck.append(f"'{dic['label']}EDITNNC.INC' /\n")
    with open(
        f"{dic['fol']}/{dic['write']}.DATA",
        "w",
        encoding="utf8",
    ) as file:
        for row in nncdeck:
            file.write(row + "\n")
    if dic["resdata"]:
        temp = ResdataFile(dic["deck"] + ".EGRID")
        coa = ResdataFile(dic["write"] + ".INIT")
        coag = ResdataFile(dic["write"] + ".EGRID")
        rnnc1 = np.array(temp.iget_kw("NNC1")[0])
        rnnc2 = np.array(temp.iget_kw("NNC2")[0])
        rnnct = np.array(dic["ini"].iget_kw("TRANNNC")[0])
        cnnc1 = np.array(coag.iget_kw("NNC1")[0])
        cnnc2 = np.array(coag.iget_kw("NNC2")[0])
        cnnct = np.array(coa.iget_kw("TRANNNC")[0])
        coag = Grid(dic["write"] + ".EGRID")
        refpv = np.array(dic["ini"].iget_kw("PORV")[0])
        coapv = np.array(coa.iget_kw("PORV")[0])
        coa_dz = np.zeros(len(coapv))
        ref_dz = np.zeros(len(refpv))
        dic["coa_tranx"] = np.zeros(len(coapv))
        dic["coa_trany"] = np.zeros(len(coapv))
        dic["coa_tranx"][coapv > 0] = np.array(coa.iget_kw("TRANX")[0])
        dic["coa_trany"][coapv > 0] = np.array(coa.iget_kw("TRANY")[0])
        coa_dz[coapv > 0] = np.array(coa.iget_kw("DZ")[0])
        ref_dz[refpv > 0] = np.array(dic["ini"].iget_kw("DZ")[0])
    else:
        temp = OpmFile(dic["deck"] + ".EGRID")
        coa = OpmFile(dic["write"] + ".INIT")
        coag = OpmFile(dic["write"] + ".EGRID")
        rnnc1 = np.array(temp["NNC1"])
        rnnc2 = np.array(temp["NNC2"])
        rnnct = np.array(dic["ini"]["TRANNNC"])
        cnnc1 = np.array(coag["NNC1"])
        cnnc2 = np.array(coag["NNC2"])
        cnnct = np.array(coa["TRANNNC"])
        coag = OpmGrid(dic["write"] + ".EGRID")
        refpv = np.array(dic["ini"]["PORV"])
        coapv = np.array(coa["PORV"])
        coa_dz = np.zeros(len(coapv))
        ref_dz = np.zeros(len(refpv))
        dic["coa_tranx"] = np.zeros(len(coapv))
        dic["coa_trany"] = np.zeros(len(coapv))
        dic["coa_tranx"][coapv > 0] = np.array(coa["TRANX"])
        dic["coa_trany"][coapv > 0] = np.array(coa["TRANY"])
        coa_dz[coapv > 0] = np.array(coa["DZ"])
        ref_dz[refpv > 0] = np.array(dic["ini"]["DZ"])
    dic["coa_editnnc"] = []
    indel = []
    for i, (r1, r2) in enumerate(zip(rnnc1, rnnc2)):
        if dic["resdata"]:
            rijk1 = dic["grid"].get_ijk(global_index=r1 - 1)
            rijk2 = dic["grid"].get_ijk(global_index=r2 - 1)
        else:
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
                if coa_dz[ind] > 0:
                    dic["coa_tranx"][ind] += rnnct[i] * ref_dz[r1 - 1] / coa_dz[ind]
            elif rijk1[1] + 1 == rijk2[1]:
                ind = (
                    (dic["ic"][rijk1[0] + 1] - 1)
                    + (dic["jc"][rijk1[1] + 1] - 1) * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                if coa_dz[ind] > 0:
                    dic["coa_trany"][ind] += rnnct[i] * ref_dz[r1 - 1] / coa_dz[ind]
            elif rijk1[0] == rijk2[0] + 1:
                ind = (
                    (dic["ic"][rijk2[0] + 1] - 1)
                    + (dic["jc"][rijk2[1] + 1] - 1) * dic["nx"]
                    + (dic["kc"][rijk2[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                if coa_dz[ind] > 0:
                    dic["coa_tranx"][ind] += rnnct[i] * ref_dz[r2 - 1] / coa_dz[ind]
            elif rijk1[1] == rijk2[1] + 1:
                ind = (
                    (dic["ic"][rijk2[0] + 1] - 1)
                    + (dic["jc"][rijk2[1] + 1] - 1) * dic["nx"]
                    + (dic["kc"][rijk2[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                if coa_dz[ind] > 0:
                    dic["coa_trany"][ind] += rnnct[i] * ref_dz[r2 - 1] / coa_dz[ind]
            indel.append(i)
    rnnc1 = np.delete(rnnc1, indel)
    rnnc2 = np.delete(rnnc2, indel)
    print("Processing the transmissibilities")
    with alive_bar(len(cnnc1)) as bar_animation:
        for n, (n1, n2) in enumerate(zip(cnnc1, cnnc2)):
            bar_animation()
            if dic["resdata"]:
                ijk1 = coag.get_ijk(global_index=n1 - 1)
                ijk2 = coag.get_ijk(global_index=n2 - 1)
            else:
                ijk1 = coag.ijk_from_global_index(n1 - 1)
                ijk2 = coag.ijk_from_global_index(n2 - 1)
            fip1 = ijk1[2] + 1
            fip2 = ijk2[2] + 1
            rtran = 0
            found = 0
            indel = []
            for i, (r1, r2) in enumerate(zip(rnnc1, rnnc2)):
                if dic["resdata"]:
                    rijk1 = dic["grid"].get_ijk(global_index=r1 - 1)
                    rijk2 = dic["grid"].get_ijk(global_index=r2 - 1)
                else:
                    rijk1 = dic["grid"].ijk_from_global_index(r1 - 1)
                    rijk2 = dic["grid"].ijk_from_global_index(r2 - 1)
                rfip1 = dic["kc"][rijk1[2] + 1]
                rfip2 = dic["kc"][rijk2[2] + 1]
                if (
                    ijk1[0] == rijk1[0]
                    and ijk2[0] == rijk2[0]
                    and ijk1[1] == rijk1[1]
                    and ijk2[1] == rijk2[1]
                    and fip1 == rfip1
                    and fip2 == rfip2
                    and fip1 != fip2
                    and (ijk1[0] != ijk2[0] or ijk1[1] != ijk2[1])
                ):
                    rtran += rnnct[i]
                    found = 1
                    indel.append(i)
            rnnc1 = np.delete(rnnc1, indel)
            rnnc2 = np.delete(rnnc2, indel)
            if found == 1:
                mult = rtran / cnnct[n]
            else:
                mult = 0
            dic["coa_editnnc"].append(
                f"{ijk1[0]+1} {ijk1[1]+1} {ijk1[2]+1} {ijk2[0]+1} {ijk2[1]+1} {ijk2[2]+1} {mult} /"
            )
    for name in ["tranx", "trany", "editnnc"]:
        dic[f"coa_{name}"] = [f"{val}" for val in dic[f"coa_{name}"]]
        dic[f"coa_{name}"].insert(0, name.upper())
        dic[f"coa_{name}"].insert(
            0,
            "-- This file was generated by pycopm https://github.com/cssr-tools/pycopm",
        )
        dic[f"coa_{name}"].append("/")
        with open(
            f"{dic['label']}{name.upper()}.INC",
            "w",
            encoding="utf8",
        ) as file:
            file.write("\n".join(dic[f"coa_{name}"]))


def write_grid(dic):
    """
    Write the corner-point grid

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    var = {"dic": dic}
    mytemplate = Template(filename=f"{dic['pat']}/template_scripts/common/grid.mako")
    filledtemplate = mytemplate.render(**var)
    with open(f"{dic['fol']}/{dic['label']}GRID.INC", "w", encoding="utf8") as f:
        f.write(filledtemplate)


def write_props(dic):
    """
    Write the modified properties

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    names = dic["props"] + dic["regions"] + dic["grids"] + dic["rptrst"] + ["porv"]
    if dic["vicinity"]:
        names += ["subtoglob"]
    print("Writing the files")
    with alive_bar(len(names)) as bar_animation:
        for name in names:
            bar_animation()
            if name == "subtoglob":
                dic[f"{name}_c"].insert(0, "OPERNUM")
            else:
                dic[f"{name}_c"].insert(0, f"{name.upper()}")
            dic[f"{name}_c"].insert(
                0,
                "-- This file was generated by pycopm https://github.com/cssr-tools/pycopm",
            )
            dic[f"{name}_c"].append("/")
            with open(
                f"{dic['fol']}/{dic['label']}{name.upper()}.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("\n".join(dic[f"{name}_c"]))
