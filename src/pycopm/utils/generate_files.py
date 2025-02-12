# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,R0801

"""
Create modified (coarser, finner, submodels, transformations) OPM files.
"""

import os
import csv
import sys
import numpy as np
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
    Main scrip to call the diffeent methods to generate the opm files

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
    if dic["mode"] in ["prep", "prep_deck", "all"]:
        os.system(f"cp {dic['pth']}.DATA {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA")
        print(
            f"\nCloning {dic['pth']}.DATA to {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA for"
            " the intial dry run to generate the grid (.EGRID) and static (.INIT) "
            "properties\n"
        )
        os.system(
            f"{dic['flow']} {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA {dic['flags']} "
            f"--output-dir={dic['fol']}"
        )
        if dic["fol"] != os.path.abspath("."):
            os.system(f"mv {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA " + f"{dic['fol']}")
        for name in [".INIT", ".EGRID"]:
            files = f"{dic['fol']}/{dic['deck']}_PREP_PYCOPM_DRYRUN" + name
            if not os.path.isfile(files):
                if name == ".INIT":
                    print(
                        f"\nThe {files} is not found, try adding the keyword INIT in"
                        f" the GRID section in the original deck {dic['deck']}.DATA\n"
                    )
                else:
                    print(
                        f"\nThe {files} is not found, try removing the keyword GRIDFILE in"
                        f" the GRID section in the original deck {dic['deck']}.DATA\n"
                    )
                sys.exit()
        print("\nThe dry run succeeded")

    if dic["mode"] in ["prep_deck", "deck", "deck_dry", "all"]:
        coarsening_dir(dic)
        dic["deck"] = f"{dic['fol']}/{dic['deck']}_PREP_PYCOPM_DRYRUN"
        for name in [".INIT", ".EGRID"]:
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
        dic["mults"] = []
        dic["special"] = []
        dic["fip"] = ""
        dic["nrptsrt"] = 0
        dic["nrptsrtc"] = 0
        dic["hasnnc"] = False
        if dic["refinement"]:
            print("\nInitializing pycopm to generate the refinned files, please wait")
        elif dic["vicinity"]:
            print("\nInitializing pycopm to generate the submodel files, please wait")
        elif dic["transform"]:
            print(
                "\nInitializing pycopm to generate the transformed files, please wait"
            )
            dic["rcijk"] = np.array([0, 0, 0])
            dic["refinement"] = True
        elif not dic["ijk"]:
            print("\nInitializing pycopm to generate the coarsened files, please wait")
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
            for name in dic["props"] + dic["regions"] + dic["grids"]:
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
        if dic["refinement"]:
            for name in dic["props"] + dic["regions"] + dic["grids"] + ["porv"]:
                dic[name] = np.zeros(dic["tc"])
                if dic["resdata"]:
                    if name == "porv":
                        dic[name] = np.divide(
                            np.array(dic["ini"].iget_kw(name.upper())[0]), dic["nc"]
                        )
                    else:
                        dic[name][dic["actind"]] = dic["ini"].iget_kw(name.upper())[0]
                else:
                    if name == "porv":
                        dic[name] = np.divide(
                            np.array(dic["ini"][name.upper()]), dic["nc"]
                        )
                    else:
                        dic[name][dic["actind"]] = dic["ini"][name.upper()]
                dic[f"{name}_c"] = [""] * (dic["nx"] * dic["ny"] * dic["nz"])
                n = 0
                for k in range(dic["zn"]):
                    for _ in range(dic["Z"][k] + 1):
                        for j in range(dic["yn"]):
                            for _ in range(dic["Y"][j] + 1):
                                for i in range(dic["xn"]):
                                    ind = i + j * dic["xn"] + k * dic["xn"] * dic["yn"]
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
            n = 0
            zti = [0, 1, 2, 3]
            zbi = [4, 5, 6, 7]
            if not dic["resdata"]:
                actnum = 1 * (dic["porv"] > 0)
                v_c = np.array(dic["grid"].cellvolumes())
                for k in range(dic["zn"]):
                    for j in range(dic["yn"]):
                        for i in range(dic["xn"]):
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
                            if actnum[ind] == 1:
                                dic["d_ax"][ind] = dic["d_x"][ind]
                                dic["d_ay"][ind] = dic["d_y"][ind]
                                dic["d_az"][ind] = dic["d_z"][ind]
                                for name in (
                                    dic["props"] + dic["regions"] + dic["grids"]
                                ):
                                    dic[name][ind] = dic["ini"][name.upper()][n]
                                if dic["show"] == "pvmean":
                                    for name in dic["props"]:
                                        dic[name][ind] *= dic["porv"][ind]
                                elif not dic["show"]:
                                    dic["permx"][ind] *= dic["d_z"][ind]
                                    dic["permy"][ind] *= dic["d_z"][ind]
                                    if dic["permz"][ind] != 0:
                                        dic["permz"][ind] = (
                                            dic["d_z"][ind] / dic["permz"][ind]
                                        )
                                    dic["poro"][ind] *= dic["porv"][ind]
                                    if "swatinit" in dic["props"]:
                                        dic["swatinit"][ind] *= dic["porv"][ind]
                                    for name in ["disperc", "thconr"]:
                                        if name in dic["grids"]:
                                            dic[name][ind] *= dic["porv"][ind]
                                    for name in dic["mults"]:
                                        dic[name][ind] *= v_c[ind]
                                    if len(dic["coardir"]) == 1 and dic["trans"] == 1:
                                        drc = dic["coardir"][0]
                                        if dic[f"tran{drc}"][ind] != 0:
                                            dic[f"tran{drc}"][ind] = (
                                                1.0 / dic[f"tran{drc}"][ind]
                                            )
                                n += 1

            else:
                zti = [2, 5, 8, 11]
                zbi = [14, 17, 20, 23]
                cxyz = dic["grid"].export_corners(dic["grid"].export_index())
                for cell in dic["grid"].cells():
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
                    if cell.active == 1:
                        dic["d_ax"][cell.global_index] = dic["d_x"][cell.global_index]
                        dic["d_ay"][cell.global_index] = dic["d_y"][cell.global_index]
                        dic["d_az"][cell.global_index] = dic["grid"].cell_dz(
                            ijk=(cell.i, cell.j, cell.k)
                        )
                        for name in dic["props"] + dic["regions"] + dic["grids"]:
                            dic[name][cell.global_index] = dic["ini"].iget_kw(
                                name.upper()
                            )[0][n]
                        if dic["show"] == "pvmean":
                            for name in dic["props"]:
                                dic[name][cell.global_index] *= dic["porv"][
                                    cell.global_index
                                ]
                        elif not dic["show"]:
                            dic["permx"][cell.global_index] *= dic["d_z"][
                                cell.global_index
                            ]
                            dic["permy"][cell.global_index] *= dic["d_z"][
                                cell.global_index
                            ]
                            if dic["permz"][cell.global_index] != 0:
                                dic["permz"][cell.global_index] = (
                                    dic["d_z"][cell.global_index]
                                    / dic["permz"][cell.global_index]
                                )
                            dic["poro"][cell.global_index] *= dic["porv"][
                                cell.global_index
                            ]
                            if "swatinit" in dic["props"]:
                                dic["swatinit"][cell.global_index] *= dic["porv"][
                                    cell.global_index
                                ]
                            for name in ["disperc", "thconr"]:
                                if name in dic["grids"]:
                                    dic[name][cell.global_index] *= dic["porv"][
                                        cell.global_index
                                    ]
                            for name in dic["mults"]:
                                dic[name][cell.global_index] *= v_c[cell.global_index]
                            if len(dic["coardir"]) == 1 and dic["trans"] == 1:
                                drc = dic["coardir"][0]
                                if dic[f"tran{drc}"][cell.global_index] != 0:
                                    dic[f"tran{drc}"][cell.global_index] = (
                                        1.0 / dic[f"tran{drc}"][cell.global_index]
                                    )
                        n += 1

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
            os.system(
                f"{dic['flow']} {dic['fol']}/{dic['write']}_CORR.DATA {dic['flags1']}"
            )
        if dic["hasnnc"] > 0:
            print("\nCall OPM Flow for a dry run of the generated model\n")
            print("\nThis is needed for the nnctrans, please wait\n")
            os.chdir(dic["fol"])
            os.system(f"{dic['flow']} {dic['fol']}/{dic['write']}.DATA {dic['flags']}")
            handle_nnc_trans(dic)
        print(
            f"\nThe generation of files succeeded, see {dic['fol']}/"
            f"{dic['write']}.DATA and {dic['fol']}/{dic['label']}*.INC"
        )

    if dic["mode"] in ["deck_dry", "dry", "all"]:
        print("\nCall OPM Flow for a dry run of the generated model\n")
        os.chdir(dic["fol"])
        os.system(f"{dic['flow']} {dic['write']}.DATA {dic['flags']}")
        print("\nThe dry run of the generated model succeeded.\n")


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
                    rijk1[0]
                    + rijk1[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                if coa_dz[ind] > 0:
                    dic["coa_tranx"][ind] += rnnct[i] * ref_dz[r1 - 1] / coa_dz[ind]
            elif rijk1[1] + 1 == rijk2[1]:
                ind = (
                    rijk1[0]
                    + rijk1[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                if coa_dz[ind] > 0:
                    dic["coa_trany"][ind] += rnnct[i] * ref_dz[r1 - 1] / coa_dz[ind]
            elif rijk1[0] == rijk2[0] + 1:
                ind = (
                    rijk2[0]
                    + rijk2[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                if coa_dz[ind] > 0:
                    dic["coa_tranx"][ind] += rnnct[i] * ref_dz[r2 - 1] / coa_dz[ind]
            elif rijk1[1] == rijk2[1] + 1:
                ind = (
                    rijk2[0]
                    + rijk2[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                if coa_dz[ind] > 0:
                    dic["coa_trany"][ind] += rnnct[i] * ref_dz[r2 - 1] / coa_dz[ind]
            indel.append(i)
    rnnc1 = np.delete(rnnc1, indel)
    rnnc2 = np.delete(rnnc2, indel)
    for n, (n1, n2) in enumerate(zip(cnnc1, cnnc2)):
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
    Write the coarser properties

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    for name in dic["props"] + dic["regions"] + dic["grids"] + ["porv"]:
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
