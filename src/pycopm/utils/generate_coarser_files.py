# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911

"""
Utiliy methods to only create the coarser files by pycopm.
"""

import os
import csv
import sys
import numpy as np
from resdata.grid import Grid
from resdata.resfile import ResdataFile
from mako.template import Template
import pandas as pd


def create_deck(dic):
    """
    Main scrip to call the diffeent methods to generate the coarser files

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
        os.system(f"cp {dic['deck']}.DATA {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA")
        print(
            f"\nCloning {dic['deck']}.DATA to {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA for"
            " the intial dry run to generate the grid (.EGRID) and static (.INIT) "
            "properties\n"
        )
        os.system(
            f"{dic['flow']} {dic['deck']}_PREP_PYCOPM_DRYRUN.DATA {dic['flags']} "
            f"--output-dir={dic['fol']}"
        )
        if dic["fol"] != ".":
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
        temp = ResdataFile(f"{dic['exe']}/" + dic["deck"] + ".EGRID")
        if temp.has_kw("NNC1") and dic["trans"] > 0:
            dic["hasnnc"] = True
        dic["grid"] = Grid(f"{dic['exe']}/" + dic["deck"] + ".EGRID")
        dic["ini"] = ResdataFile(f"{dic['exe']}/" + dic["deck"] + ".INIT")
        if not dic["ijk"]:
            print("\nInitializing pycopm to generate the coarse files, please wait")
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
        if dic["trans"] > 0:
            for name in ["tranx", "trany", "tranz"]:
                dic["props"] += [name]
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
                if max(dic["ini"].iget_kw(name.upper())[0]) > 1:
                    dic["regions"] += [name]
        nc = dic["grid"].nx * dic["grid"].ny * dic["grid"].nz
        dic["con"] = np.array([0 for _ in range(nc)])
        handle_clusters(dic)
        map_ijk(dic)
        if dic["ijk"]:
            print(
                dic["ic"][dic["ijk"][0]],
                dic["jc"][dic["ijk"][1]],
                dic["kc"][dic["ijk"][2]],
            )
            sys.exit()
        dic["porv"] = np.array(dic["ini"].iget_kw("PORV")[0])
        actnum = np.array([0 for _ in range(nc)])
        for i in ["x", "y", "z"]:
            dic[f"d_{i}"] = np.array([np.nan for _ in range(nc)])
            dic[f"d_a{i}"] = np.array([np.nan for _ in range(nc)])
        v_c = np.array([np.nan for _ in range(nc)])
        z_t = np.array([np.nan for _ in range(nc)])
        z_b = np.array([np.nan for _ in range(nc)])
        z_b_t = np.array([np.nan for _ in range(nc)])
        for name in dic["props"] + dic["regions"] + dic["grids"]:
            dic[name] = 1.0 * np.ones(nc) * np.nan
        n = 0
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
            z_t[cell.global_index] = min(cxyz[cell.global_index][i] for i in zti)
            z_b[cell.global_index] = max(cxyz[cell.global_index][i] for i in zti)
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
                    dic[name][cell.global_index] = dic["ini"].iget_kw(name.upper())[0][
                        n
                    ]
                    if dic["show"] == "pvmean":
                        dic[name][cell.global_index] *= dic["porv"][cell.global_index]
                if not dic["show"]:
                    dic["permx"][cell.global_index] *= dic["d_z"][cell.global_index]
                    dic["permy"][cell.global_index] *= dic["d_z"][cell.global_index]
                    if dic["permz"][cell.global_index] != 0:
                        dic["permz"][cell.global_index] = (
                            dic["d_z"][cell.global_index]
                            / dic["permz"][cell.global_index]
                        )
                    dic["poro"][cell.global_index] *= dic["porv"][cell.global_index]
                    if "swatinit" in dic["props"]:
                        dic["swatinit"][cell.global_index] *= dic["porv"][
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
        clusmin, clusmax, rmv = map_properties(dic, actnum, z_t, z_b, z_b_t, v_c)
        if dic["pvcorr"] == 1:
            handle_pv(dic, clusmin, clusmax, rmv)
        handle_cp_grid(dic)
        write_grid(dic)
        write_props(dic)
        with open(
            f"{dic['exe']}/{dic['fol']}/{dic['write']}.DATA",
            "w",
            encoding="utf8",
        ) as file:
            for row in dic["lol"]:
                file.write(row + "\n")
        if dic["fipcorr"] == 1:
            thr = 1e-1
            with open(
                f"{dic['exe']}/{dic['fol']}/{dic['write']}_2DAYS.DATA",
                "w",
                encoding="utf8",
            ) as file:
                for row in dic["lolc"]:
                    file.write(row + "\n")
            with open(
                f"{dic['exe']}/{dic['fol']}/{dic['write']}_CORR.DATA",
                "w",
                encoding="utf8",
            ) as file:
                for row in dic["deckcorr"]:
                    file.write(row + "\n")
            os.system(f"{dic['flow']} {dic['write']}_CORR.DATA {dic['flags1']}")
            os.system(f"{dic['flow']} {dic['write']}_2DAYS.DATA {dic['flags1']}")
            ref = ResdataFile(f"{dic['exe']}/" + dic["write"] + "_2DAYS.UNRST")
            cor = ResdataFile(f"{dic['exe']}/" + dic["write"] + "_CORR.UNRST")
            cori = ResdataFile(f"{dic['exe']}/" + dic["write"] + "_CORR.INIT")
            ref_fipg = np.array(ref.iget_kw("FIPGAS")[0])
            ref_fipo = np.array(ref.iget_kw("FIPOIL")[0])
            cor_pv = np.array(cori.iget_kw("PORV")[0])
            cor_pa = cor_pv[cor_pv > 0]
            cor_fipg = np.array(cor.iget_kw("FIPGAS")[0])
            cor_fipo = np.array(cor.iget_kw("FIPOIL")[0])
            fact = sum(ref_fipo) / sum(cor_fipo) - 1
            cor_pa[cor_fipo <= thr] -= (
                fact * sum(cor_pa[cor_fipo > thr]) / len(cor_pa[cor_fipo <= thr])
            )
            cor_pa[cor_fipo > thr] *= 1 + fact
            cor_pv[cor_pv > 0] = cor_pa
            with open(
                f"{dic['exe']}/{dic['fol']}/{dic['label']}PORV.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("PORV\n")
                file.write("\n".join(f"{val}" for val in cor_pv))
                file.write("\n/")
            os.system(f"{dic['flow']} {dic['write']}_CORR.DATA {dic['flags1']}")
            cor = ResdataFile(f"{dic['exe']}/" + dic["write"] + "_CORR.UNRST")
            cori = ResdataFile(f"{dic['exe']}/" + dic["write"] + "_CORR.INIT")
            cor_pv = np.array(cori.iget_kw("PORV")[0])
            cor_pa = cor_pv[cor_pv > 0]
            cor_fipg = np.array(cor.iget_kw("FIPGAS")[0])
            cor_fipo = np.array(cor.iget_kw("FIPOIL")[0])
            cor_sgas = np.array(cor.iget_kw("SGAS")[0])
            fact = (sum(ref_fipg) - sum(cor_fipg)) / sum(cor_fipg[cor_sgas > thr])
            cor_pa[cor_fipo <= thr] -= (
                fact * sum(cor_pa[cor_sgas > thr]) / len(cor_pa[cor_fipo <= thr])
            )
            cor_pa[cor_sgas > thr] *= 1 + fact
            cor_pv[cor_pv > 0] = cor_pa
            with open(
                f"{dic['exe']}/{dic['fol']}/{dic['label']}PORV.INC",
                "w",
                encoding="utf8",
            ) as file:
                file.write("PORV\n")
                file.write("\n".join(f"{val}" for val in cor_pv))
                file.write("\n/")
            os.system(f"{dic['flow']} {dic['write']}_CORR.DATA {dic['flags1']}")
        if dic["hasnnc"] > 0:
            print("\nCall OPM Flow for a dry run of the coarse model\n")
            print("\nThis is needed for the nnctrans, please wait\n")
            os.chdir(dic["fol"])
            os.system(f"{dic['flow']} {dic['write']}.DATA {dic['flags']}")
            handle_nnc_trans(dic)
        print(
            f"\nThe generation of coarse files succeeded, see {dic['fol']}/"
            f"{dic['write']}.DATA and {dic['fol']}/{dic['label']}*.INC"
        )

    if dic["mode"] in ["deck_dry", "dry", "all"]:
        print("\nCall OPM Flow for a dry run of the coarse model\n")
        os.chdir(dic["fol"])
        os.system(f"{dic['flow']} {dic['write']}.DATA {dic['flags']}")
        print("\nThe dry run of the coarse model succeeded\n")


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
        f"{dic['exe']}/{dic['fol']}/{dic['write']}.DATA",
        "w",
        encoding="utf8",
    ) as file:
        for row in nncdeck:
            file.write(row + "\n")
    temp = ResdataFile(f"{dic['exe']}/" + dic["deck"] + ".EGRID")
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
    dic["coa_editnnc"] = []
    indel = []
    for i, (r1, r2) in enumerate(zip(rnnc1, rnnc2)):
        rijk1 = dic["grid"].get_ijk(global_index=r1 - 1)
        rijk2 = dic["grid"].get_ijk(global_index=r2 - 1)
        if dic["kc"][rijk1[2] + 1] == dic["kc"][rijk2[2] + 1] and (
            rijk1[0] != rijk2[0] or rijk1[1] != rijk2[1]
        ):
            if rijk1[0] + 1 == rijk2[0]:
                ind = (
                    rijk1[0]
                    + rijk1[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_tranx"][ind] += rnnct[i] * ref_dz[r1 - 1] / coa_dz[ind]
            elif rijk1[1] + 1 == rijk2[1]:
                ind = (
                    rijk1[0]
                    + rijk1[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_trany"][ind] += rnnct[i] * ref_dz[r1 - 1] / coa_dz[ind]
            elif rijk1[0] == rijk2[0] + 1:
                ind = (
                    rijk2[0]
                    + rijk2[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_tranx"][ind] += rnnct[i] * ref_dz[r2 - 1] / coa_dz[ind]
            elif rijk1[1] == rijk2[1] + 1:
                ind = (
                    rijk2[0]
                    + rijk2[1] * dic["nx"]
                    + (dic["kc"][rijk1[2] + 1] - 1) * dic["nx"] * dic["ny"]
                )
                dic["coa_trany"][ind] += rnnct[i] * ref_dz[r2 - 1] / coa_dz[ind]
            indel.append(i)
    rnnc1 = np.delete(rnnc1, indel)
    rnnc2 = np.delete(rnnc2, indel)
    for n, (n1, n2) in enumerate(zip(cnnc1, cnnc2)):
        ijk1 = coag.get_ijk(global_index=n1 - 1)
        ijk2 = coag.get_ijk(global_index=n2 - 1)
        fip1 = ijk1[2] + 1
        fip2 = ijk2[2] + 1
        rtran = 0
        found = 0
        indel = []
        for i, (r1, r2) in enumerate(zip(rnnc1, rnnc2)):
            rijk1 = dic["grid"].get_ijk(global_index=r1 - 1)
            rijk2 = dic["grid"].get_ijk(global_index=r2 - 1)
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


def map_properties(dic, actnum, z_t, z_b, z_b_t, v_c):
    """
    Mapping to the coarse properties

    Args:
        dic (dict): Global dictionary\n
        actnum (array): Integers with the active cells\n
        z_t (array): Floats with the top cell z-center position\n
        z_b (array): Floats with the bottom cell z-center position

    Returns:
        dic (dict): Modified global dictionary

    """
    clusmax = pd.Series(actnum).groupby(dic["con"]).max()
    clusming = pd.Series(actnum).groupby(dic["con"]).min()
    clusmode = (
        pd.Series(actnum).groupby(dic["con"]).agg(lambda x: pd.Series.mode(x).iat[0])
    )
    freq = pd.Series(actnum).groupby(dic["con"]).sum()
    dz_c = pd.Series(z_b_t).groupby(dic["con"]).mean()
    for i in ["x", "y", "z"]:
        dic[f"{i}_tot"] = pd.Series(dic[f"d_{i}"]).groupby(dic["con"]).sum()
        dic[f"{i}a_tot"] = pd.Series(dic[f"d_a{i}"]).groupby(dic["con"]).sum()
    v_tot = pd.Series(v_c).groupby(dic["con"]).sum()
    if len(dic["how"]) == 1:
        if dic["how"][0] == "min":
            clusmin = clusming
            clust = clusmin
        elif dic["how"][0] == "mode":
            clusmin = clusmode
            clust = clusmin
        else:
            clusmin = clusmax
            clust = clusmax
    else:
        clusmin = 1 * freq
        clust = 1 * freq
        for k, val in enumerate(dic["how"]):
            if val == "min":
                clusmin[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ] = clusming[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ]
                clust[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ] = clusming[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ]
            elif val == "mode":
                clusmin[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ] = clusmode[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ]
                clust[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ] = clusmode[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ]
            else:
                clusmin[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ] = clusmax[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ]
                clust[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ] = clusmax[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ]
    if dic["jump"][0]:
        if len(dic["jump"]) == 1:
            rmv = 1 * (
                (
                    pd.Series(z_b).groupby(dic["con"]).max()
                    - pd.Series(z_t).groupby(dic["con"]).min()
                )
                < float(dic["jump"][0]) * dz_c
            )
        else:
            rmv = 0.0 * freq
            deltaz = (
                pd.Series(z_b).groupby(dic["con"]).max()
                - pd.Series(z_t).groupby(dic["con"]).min()
            )
            for k, val in enumerate(dic["jump"]):
                rmv[
                    k * dic["nx"] * dic["ny"] + 1 : (k + 1) * dic["nx"] * dic["ny"] + 2
                ] = (
                    1
                    * (deltaz < float(val) * dz_c)[
                        k * dic["nx"] * dic["ny"]
                        + 1 : (k + 1) * dic["nx"] * dic["ny"]
                        + 2
                    ]
                )
        dic["actnum_c"] = [int(val * r_m) for val, r_m in zip(clust, rmv)]
    else:
        rmv = 0 * dz_c + 1
        dic["actnum_c"] = [int(val) for val in clust]
    p_vs = pd.Series(dic["porv"]).groupby(dic["con"]).sum()
    dic["porv_c"] = [f"{val}" for val in p_vs]
    drc = dic["coardir"][0]
    for name in dic["props"]:
        if not dic["show"]:
            c_c = pd.Series(dic[name]).groupby(dic["con"]).sum()
            if name in ["permx", "permy"]:
                dic[f"{name}_c"] = [
                    f"{val/h_t}" if h_t * val > 0 else "0"
                    for val, h_t in zip(c_c, dic["z_tot"])
                ]
            elif name == "tranx":
                if "x" in dic["coardir"]:
                    if dic["trans"] == 1:
                        c_m = pd.Series(dic[name]).groupby(dic["con"]).min()
                        dic[f"{name}_c"] = [
                            f"{l_t/val}" if m_v * val > 0 else "0"
                            for val, m_v, l_t in zip(c_c, c_m, dic[f"{drc}_tot"])
                        ]
                    else:
                        # conxs = pd.Series(dic[name]).groupby(dic["con"]).agg(lambda x:
                        # sum(max(list(x)[i],np.roll(x, 2)[i])>0 for i in
                        # range(int(len(x)/2))) == int(len(x)/2))
                        # conys = pd.Series(dic["trany"]).groupby(dic["con"]).agg(lambda x:
                        # sum(max(list(x)[2*i],list(x)[2*i+1])>0 for i in range(int(len(x)/2)-1))
                        # == int(len(x)/2)-1)
                        c_ls = pd.Series(dic[name]).groupby(dic["con"]).mean()
                        d_ls = pd.Series(dic[name]).groupby(dic["con"]).min()
                        # d_ls = pd.Series(dic[f"d_x"]).groupby(dic["con"]).mean()
                        # dic[f"{name}_c"] = [f"{val*d_l/l_t}" if val*conx*cony > 0 else "0" for
                        # val, d_l, l_t, conx, cony in zip(c_ls, d_ls, dic[f"x_tot"], conxs, conys)]
                        dic[f"{name}_c"] = [
                            f"{val}" if d_l > 0 else "0" for val, d_l in zip(c_ls, d_ls)
                        ]
                else:
                    dic[f"{name}_c"] = [
                        f"{val*l_a/l_t}" if val > 0 else "0"
                        for val, l_a, l_t in zip(
                            c_c, dic[f"{drc}a_tot"], dic[f"{drc}_tot"]
                        )
                    ]
            elif name == "trany":
                if "y" in dic["coardir"]:
                    if dic["trans"] == 1:
                        c_m = pd.Series(dic[name]).groupby(dic["con"]).min()
                        dic[f"{name}_c"] = [
                            f"{l_t/val}" if m_v * val > 0 else "0"
                            for val, m_v, l_t in zip(c_c, c_m, dic[f"{drc}_tot"])
                        ]
                    else:
                        # conxs = pd.Series(dic["tranx"]).groupby(dic["con"]).agg(lambda
                        # x: sum(max(list(x)[i],np.roll(x, 2)[i])>0 for i in
                        # range(int(len(x)/2)-1)) == int(len(x)/2)-1)
                        # conys = pd.Series(dic[name]).groupby(dic["con"]).agg(lambda
                        # x: sum(max(list(x)[2*i],list(x)[2*i+1])>0 for i in
                        # range(int(len(x)/2))) == int(len(x)/2))
                        c_ls = pd.Series(dic[name]).groupby(dic["con"]).mean()
                        d_ls = pd.Series(dic[name]).groupby(dic["con"]).min()
                        # d_ls = pd.Series(dic[f"d_y"]).groupby(dic["con"]).mean()
                        # dic[f"{name}_c"] = [f"{val*d_l/l_t}" if val*conx*cony > 0
                        # else "0" for val, d_l, l_t, conx, cony in zip(c_ls, d_ls,
                        # dic[f"y_tot"], conxs, conys)]
                        dic[f"{name}_c"] = [
                            f"{val}" if d_l > 0 else "0" for val, d_l in zip(c_ls, d_ls)
                        ]
                else:
                    dic[f"{name}_c"] = [
                        f"{val*l_a/l_t}" if val > 0 else "0"
                        for val, l_a, l_t in zip(
                            c_c, dic[f"{drc}a_tot"], dic[f"{drc}_tot"]
                        )
                    ]
            elif name == "tranz":
                if "z" in dic["coardir"]:
                    if dic["trans"] == 1:
                        c_m = pd.Series(dic[name]).groupby(dic["con"]).min()
                        l_as = pd.Series(dic["d_az"]).groupby(dic["con"]).mean()
                        c_c[: -dic["nx"] * dic["ny"]] = (
                            (
                                np.array(c_c[: -dic["nx"] * dic["ny"]])
                                + np.array(c_c[dic["nx"] * dic["ny"] :])
                            )
                            * (np.array(c_m[: -dic["nx"] * dic["ny"]] > 0))
                            * (np.array(c_m[dic["nx"] * dic["ny"] :] > 0))
                        )
                        dic[f"{name}_c"] = [
                            f"{1.*l_a/(val * l_t)}" if val > 0 else "0"
                            for val, l_t, l_a in zip(c_c, dic[f"{drc}_tot"], l_as)
                        ]
                    else:
                        c_ls = pd.Series(dic[name]).groupby(dic["con"]).last()
                        d_ls = pd.Series(dic["d_z"]).groupby(dic["con"]).last()
                        dic[f"{name}_c"] = [
                            f"{val*d_l/l_t}" if val > 0 else "0"
                            for val, d_l, l_t in zip(c_ls, d_ls, dic[f"{drc}_tot"])
                        ]
                else:
                    dic[f"{name}_c"] = [
                        f"{val*l_a/l_t}" if val > 0 else "0"
                        for val, l_a, l_t in zip(
                            c_c, dic[f"{drc}a_tot"], dic[f"{drc}_tot"]
                        )
                    ]
            elif name == "permz":
                dic["permz_c"] = [
                    f"{h_t/val}" if h_t * val > 0 else "0"
                    for val, h_t in zip(c_c, dic["za_tot"])
                ]
            elif name in ["poro", "swatinit"]:
                dic[f"{name}_c"] = [
                    f"{val/p_v}" if p_v > 0 else "0" for val, p_v in zip(c_c, p_vs)
                ]
            else:
                dic[f"{name}_c"] = [
                    f"{val/v_t}" if v_t > 0 else "0" for val, v_t in zip(c_c, v_tot)
                ]
        else:
            if dic["show"] == "min":
                c_c = pd.Series(dic[name]).groupby(dic["con"]).min()
                dic[f"{name}_c"] = [f"{val}" for val in c_c]
            elif dic["show"] == "max":
                c_c = pd.Series(dic[name]).groupby(dic["con"]).max()
                dic[f"{name}_c"] = [f"{val}" for val in c_c]
            elif dic["show"] == "pvmean":
                c_c = pd.Series(dic[name]).groupby(dic["con"]).sum()
                dic[f"{name}_c"] = [
                    f"{val/p_v}" if p_v > 0 else "0" for val, p_v in zip(c_c, p_vs)
                ]
            else:
                c_c = pd.Series(dic[name]).groupby(dic["con"]).sum()
                dic[f"{name}_c"] = [
                    f"{val/fre}" if fre > 0 else "0" for val, fre in zip(c_c, freq)
                ]
    for name in dic["regions"] + dic["grids"]:
        if dic["nhow"] == "min":
            c_c = pd.Series(dic[name]).groupby(dic["con"]).min()
            dic[f"{name}_c"] = [
                f"{int(val)}" if not np.isnan(val) else "0" for val in c_c
            ]
        elif dic["nhow"] == "max":
            c_c = pd.Series(dic[name]).groupby(dic["con"]).max()
            dic[f"{name}_c"] = [
                f"{int(val)}" if not np.isnan(val) else "0" for val in c_c
            ]
        else:
            c_c = (
                pd.Series(dic[name])
                .groupby(dic["con"])
                .agg(lambda x: list(pd.Series.mode(x)))
            )
            dic[f"{name}_c"] = [
                f"{int(val[0])}" if len(val) > 0 else "0" for val in c_c
            ]
    return clusmin, clusmax, rmv


def handle_pv(dic, clusmin, clusmax, rmv):
    """
    Make sure the pore volume is not created nor destroyed, only distributed

    Args:
        dic (dict): Global dictionary\n
        clusmin (pandas dataFrame): Mask with all active cells in cluster\n
        clusmax (pandas dataFrame): Mask with at least one active cell in cluster\n
        rmv (pandas dataFrame): Mask to remove cells by the argument flag jump

    Returns:
        dic (dict): Modified global dictionary

    """
    porv = pd.Series(dic["porv"]).groupby(dic["con"]).sum()
    maxn = max(dic["nx"], dic["ny"], dic["nz"])
    for i_d in porv[clusmax - clusmin > 0].keys().union(rmv[rmv == 0].keys()):
        search = True
        n, s = 0, 0
        ind = []
        dic["i"], dic["j"], dic["k"] = get_ijk(dic, i_d - 1)
        while search:
            ind = find_neighbors(dic, ind, i_d, n, s)
            if ind:
                for num in ind:
                    dic["porv_c"][
                        num
                    ] = f"{float(dic['porv_c'][num])+porv[i_d]/len(ind)}"
                break
            n += 1
            if maxn < n:
                n = 0
                s += 1


def find_neighbors(dic, ind, i_d, n, s):
    """
    Find the neighbouring cells to distribute the removed pore volume

    Args:
        dic (dict): Global dictionary\n
        ind (list): Indices os cells to distribute the pore volume\n
        i_d (int): Index of the removed cell to distribute its pore volume\n
        n (int): Current increased index for the neighbours search\n
        s (int): Shift to neighbours cells

    Returns:
        ind (list): Indices os cells to distribute the pore volume\n
        dic (dict): Modified global dictionary

    """
    if dic["i"] + 1 + n < dic["nx"] and i_d + n + s < dic["nx"] * dic["ny"] * dic["nz"]:
        if dic["actnum_c"][i_d + n + s] == 1:
            ind.append(i_d + n + s)
    if -1 < dic["i"] - 1 - n and i_d - 2 - n + s < dic["nx"] * dic["ny"] * dic["nz"]:
        if dic["actnum_c"][i_d - 2 - n + s] == 1:
            ind.append(i_d - 2 - n + s)
    if (
        dic["j"] + 1 + n < dic["ny"]
        and i_d - 1 + (n + 1) * dic["nx"] + s < dic["nx"] * dic["ny"] * dic["nz"]
    ):
        if dic["actnum_c"][i_d - 1 + (n + 1) * dic["nx"] + s] == 1:
            ind.append(i_d - 1 + (n + 1) * dic["nx"] + s)
    if (
        -1 < dic["j"] - 1 - n
        and i_d - 1 - (n + 1) * dic["nx"] + s < dic["nx"] * dic["ny"] * dic["nz"]
    ):
        if dic["actnum_c"][i_d - 1 - (n + 1) * dic["nx"] + s] == 1:
            ind.append(i_d - 1 - (n + 1) * dic["nx"] + s)
    if (
        dic["k"] + 1 + n < dic["nz"]
        and i_d - 1 + (n + 1) * dic["nx"] * dic["ny"] + s
        < dic["nx"] * dic["ny"] * dic["nz"]
    ):
        if dic["actnum_c"][i_d - 1 + (n + 1) * dic["nx"] * dic["ny"] + s] == 1:
            ind.append(i_d - 1 + (n + 1) * dic["nx"] * dic["ny"] + s)
    if (
        -1 < dic["k"] - 1 - n
        and i_d - 1 - (n + 1) * dic["nx"] * dic["ny"] + s
        < dic["nx"] * dic["ny"] * dic["nz"]
    ):
        if dic["actnum_c"][i_d - 1 - (n + 1) * dic["nx"] * dic["ny"] + s] == 1:
            ind.append(i_d - 1 - (n + 1) * dic["nx"] * dic["ny"] + s)
    return ind


def get_ijk(dic, i_d):
    """
    Return the i,j, and k index from the global index

    Args:
        dic (dict): Global dictionary\n
        i_d (int): Index of the removed cell to distribute its pore volume

    Returns:
        i,j,k (int): i,j, and k cell indices

    """
    k = int(i_d / (dic["nx"] * dic["ny"]))
    j = int((i_d - k * dic["nx"] * dic["ny"]) / dic["nx"])
    i = i_d - j * dic["nx"] - k * dic["nx"] * dic["ny"]
    return i, j, k


def coarsening_dir(dic):
    """
    Get the coarsenign directions

    Args:
        dic (dict): Global dictionary

    Returns:
         dic (dict): Modified global dictionary

    """
    dic["coardir"] = ""
    if len(dic["cijk"]) > 2:
        for i, drc in enumerate(["x", "y", "z"]):
            if dic["cijk"][i] > 1:
                dic["coardir"] += drc
    else:
        for drc in ["x", "y", "z"]:
            if dic[f"{drc}coar"]:
                dic["coardir"] += drc


def write_grid(dic):
    """
    Write the corner-point grid

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    if dic["fol"] != ".":
        dic["files"] = [f for f in os.listdir(f"{dic['exe']}") if f.endswith(".INC")]
        for file in dic["files"]:
            copy = True
            for prop in dic["props"] + dic["regions"] + dic["grids"] + ["porv"]:
                if prop in file:
                    copy = False
            if copy:
                os.system(f"scp -r {dic['exe']}/{file} {dic['exe']}/{dic['fol']}")
    var = {"dic": dic}
    mytemplate = Template(filename=f"{dic['pat']}/template_scripts/common/grid.mako")
    filledtemplate = mytemplate.render(**var)
    with open(
        f"{dic['exe']}/{dic['fol']}/{dic['label']}GRID.INC", "w", encoding="utf8"
    ) as f:
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
            f"{dic['exe']}/{dic['fol']}/{dic['label']}{name.upper()}.INC",
            "w",
            encoding="utf8",
        ) as file:
            file.write("\n".join(dic[f"{name}_c"]))


def handle_clusters(dic):
    """
    Create the coarser clusters

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["X"] = np.zeros(dic["grid"].nx + 1)
    dic["Y"] = np.zeros(dic["grid"].ny + 1)
    dic["Z"] = np.zeros(dic["grid"].nz + 1)
    if len(dic["cijk"]) > 2:
        dic["X"] = 2 * np.ones(dic["grid"].nx + 1)
        dic["Y"] = 2 * np.ones(dic["grid"].ny + 1)
        dic["Z"] = 2 * np.ones(dic["grid"].nz + 1)
        dic["X"][range(0, dic["grid"].nx, dic["cijk"][0])] = 0
        dic["Y"][range(0, dic["grid"].ny, dic["cijk"][1])] = 0
        dic["Z"][range(0, dic["grid"].nz, dic["cijk"][2])] = 0
        dic["X"][-1], dic["Y"][-1], dic["Z"][-1] = 0, 0, 0
    else:
        for i in ["x", "y", "z"]:
            if dic[f"{i}coar"]:
                dic[i.upper()] = np.array(dic[f"{i}coar"])
    n = 0
    m = 1
    for k in range(dic["grid"].nz):
        for j in range(dic["grid"].ny):
            for i in range(dic["grid"].nx):
                if dic["con"][n] == 0:
                    dic["con"][n] = m
                    m += 1
                if (dic["X"][i + 1]) > 1:
                    dic["con"][n + 1] = dic["con"][n]
                if (dic["Y"][j + 1]) > 1:
                    dic["con"][n + dic["grid"].nx] = dic["con"][n]
                if (dic["Z"][k + 1]) > 1:
                    dic["con"][n + dic["grid"].nx * dic["grid"].ny] = dic["con"][n]
                n += 1

    dic["nx"] = dic["grid"].nx - int(sum(dic["X"] == 2))
    dic["ny"] = dic["grid"].ny - int(sum(dic["Y"] == 2))
    dic["nz"] = dic["grid"].nz - int(sum(dic["Z"] == 2))


def map_ijk(dic):
    """
    Create the mappings to the new i,j,k indices

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["ic"] = np.array([0 for _ in range(dic["grid"].nx + 1)])
    dic["jc"] = np.array([0 for _ in range(dic["grid"].ny + 1)])
    dic["kc"] = np.array([0 for _ in range(dic["grid"].nz + 1)])
    n = 1
    m = 1
    for i in range(dic["grid"].nx):
        if dic["ic"][n] == 0:
            dic["ic"][n] = m
            m += 1
        if (dic["X"][i + 1]) > 1:
            dic["ic"][n + 1] = dic["ic"][n]
        n += 1
    n = 1
    m = 1
    for j in range(dic["grid"].ny):
        if dic["jc"][n] == 0:
            dic["jc"][n] = m
            m += 1
        if (dic["Y"][j + 1]) > 1:
            dic["jc"][n + 1] = dic["jc"][n]
        n += 1
    n = 1
    m = 1
    for k in range(dic["grid"].nz):
        if dic["kc"][n] == 0:
            dic["kc"][n] = m
            m += 1
        if (dic["Z"][k + 1]) > 1:
            dic["kc"][n + 1] = dic["kc"][n]
        n += 1


def handle_cp_grid(dic):
    """
    Handle the pillars and zcord for the coarser grid

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    ir = []
    mr = []
    zc = dic["grid"].export_zcorn()
    cr = dic["grid"].export_coord()
    for i in range(dic["grid"].nx + 1):
        if (dic["X"][i]) > 1:
            for m in range(
                i, (dic["grid"].nx + 1) * (dic["grid"].ny + 1), dic["grid"].nx + 1
            ):
                for l in range(6):
                    mr.append(m * 6 + l)
            for n in range(
                2 * i - 1,
                8 * dic["grid"].nx * dic["grid"].ny * dic["grid"].nz,
                2 * dic["grid"].nx,
            ):
                ir.append(n)
                ir.append(n + 1)

    for j in range(dic["grid"].ny + 1):
        if (dic["Y"][j]) > 1:
            for m in range(j * (dic["grid"].nx + 1), (j + 1) * (dic["grid"].nx + 1)):
                for l in range(6):
                    mr.append(m * 6 + l)
            for n in range(
                (2 * j - 1) * 2 * dic["grid"].nx,
                8 * dic["grid"].nx * dic["grid"].ny * dic["grid"].nz,
                4 * dic["grid"].nx * dic["grid"].ny,
            ):
                for l in range(4 * dic["grid"].nx):
                    ir.append(n + l)

    ir = handle_zcorn(dic, ir)
    dic["zc"] = np.delete(zc, ir, 0)
    dic["cr"] = np.delete(cr, mr, 0)


def handle_zcorn(dic, ir):
    """
    Process the zcorn

    Args:
        dic (dict): Global dictionary\n
        ir (list): Z coordinates from the corners

    Returns:
        ir (list): Modified z coordinates

    """
    for k in range(dic["grid"].nz + 1):
        if (dic["Z"][k]) > 1:
            for n in range(
                (2 * k - 1) * 4 * dic["grid"].nx * dic["grid"].ny,
                (2 * k + 1) * 4 * dic["grid"].nx * dic["grid"].ny,
            ):
                ir.append(n)
    return ir


def process_the_deck(dic):
    """
    Identify and modified the required keywords

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["lol"], dic["lolc"] = [], []
    dic["dimens"] = False
    dic["removeg"] = False
    dic["welspecs"] = False
    dic["compdat"] = False
    dic["compsegs"] = False
    dic["mapaxes"] = False
    dic["edit"] = False
    dic["editnnc"] = False
    dic["multiply"] = False
    dic["prop"] = False
    dic["oper"] = False
    dic["region"] = False
    dic["schedule"] = False
    dic["fault"] = False
    dic["rptsrt"] = False
    dic["multflt"] = False
    with open(dic["deck"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            if 0 < nrwo.find("\\t"):
                nrwo = nrwo.replace("\\t", " ")
            if not dic["schedule"]:
                dic["lolc"].append(nrwo)
            if nrwo == "DIMENS":
                dic["dimens"] = True
                continue
            if dic["dimens"]:
                if "/" in nrwo:
                    dic["dimens"] = False
                continue
            if handle_grid_props(dic, nrwo):
                continue
            if handle_props(dic, nrwo):
                continue
            if handle_regions(dic, nrwo):
                continue
            if handle_schedule(dic, nrwo):
                continue
            if handle_wells(dic, nrwo):
                continue
            if handle_segmented_wells(dic, nrwo):
                continue
            for case in dic["special"]:
                if (
                    case + "." in nrwo.lower()
                    or "." + case in nrwo.lower()
                    or "swinitial." in nrwo.lower()
                ):
                    nrwo = f"{dic['label']}{case.upper()}.INC/"
            dic["lol"].append(nrwo)


def handle_props(dic, nrwo):
    """
    Handle the props sections

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "PROPS" and not dic["prop"]:
        dic["prop"] = True
        dic["lol"].append(nrwo + "\n")
        return True
    if dic["prop"]:
        if handle_oper(dic, nrwo):
            return True
        if nrwo in ["REGIONS", "SOLUTION"]:
            dic["prop"] = False
    return False


def handle_oper(dic, nrwo):
    """
    We also support operations

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo in ["EQUALS", "COPY", "ADD", "MULTIPLY"]:
        if not dic["prop"] and nrwo == "COPY":
            return False
        dic["oper"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["oper"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["oper"] = False
        if len(edit) > 7:
            if edit[0][:2] != "--":
                if "PERM" in edit[0]:
                    edit[1] = "1"
                edit[2] = str(dic["ic"][int(edit[2])])
                edit[3] = str(dic["ic"][int(edit[3])])
                edit[4] = str(dic["jc"][int(edit[4])])
                edit[5] = str(dic["jc"][int(edit[5])])
                edit[6] = str(dic["kc"][int(edit[6])])
                edit[7] = str(dic["kc"][int(edit[7])])
                dic["lol"].append(" ".join(edit))
                return True
        if not dic["prop"]:
            dic["lol"].append(nrwo)
    return False


def handle_schedule(dic, nrwo):
    """
    Handle the schedule sections

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if dic["rptsrt"]:
        edit = nrwo.split()
        if "RFIP" not in edit or "FIP" not in edit:
            dic["fip"] = " ".join(edit[:-2] + ["FIP"] + [edit[-1]])
            dic["nrptsrt"] = len(dic["lol"])
            dic["nrptsrtc"] = len(dic["lolc"]) - 1
        dic["rptsrt"] = False
    if nrwo == "RPTRST" and dic["fipcorr"] == 1:
        dic["rptsrt"] = True
    if nrwo == "SCHEDULE" and not dic["schedule"]:
        dic["schedule"] = True
        dic["lol"].append(nrwo + "\n")
        if dic["fipcorr"] == 1:
            dic["deckcorr"] = dic["lol"].copy()
            if dic["nrptsrt"] > 0:
                dic["deckcorr"][dic["nrptsrt"]] = dic["fip"]
                dic["lolc"][dic["nrptsrtc"]] = dic["fip"]
            dic["deckcorr"].append("TSTEP")
            dic["deckcorr"].append("2 /")
            dic["lolc"].append("TSTEP")
            dic["lolc"].append("2 /")
        return True
    return False


def handle_regions(dic, nrwo):
    """
    Handle the regions sections

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "REGIONS" and not dic["region"]:
        dic["region"] = True
        dic["lol"].append(nrwo + "\n")
        return True
    if dic["region"]:
        if nrwo == "SOLUTION":
            dic["region"] = False
            for name in dic["regions"]:
                dic["lol"].append("INCLUDE")
                dic["lol"].append(f"'{dic['label']}{name.upper()}.INC' /\n")
        else:
            return True
    return False


def handle_grid_props(dic, nrwo):
    """
    Handle the grid and props sections

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "GRID" and not dic["removeg"]:
        dic["removeg"] = True
        dic["lol"].append(nrwo + "\n")
        dic["lol"].append("INIT")
        for name in dic["base"] + dic["grids"] + dic["mults"]:
            dic["lol"].append("INCLUDE")
            dic["lol"].append(f"'{dic['label']}{name.upper()}.INC' /\n")
        return True
    if dic["removeg"]:
        if handle_fault(dic, nrwo):
            return True
        if handle_mapaxes(dic, nrwo):
            return True
        if handle_multflt(dic, nrwo):
            return True
        # if handle_oper(dic, nrwo):
        #    return True
        if nrwo == "EDIT" and dic["trans"] == 0:
            dic["edit"] = True
            dic["lol"].append(nrwo)
            dic["lol"].append("INCLUDE")
            dic["lol"].append(f"'{dic['label']}PORV.INC' /\n")
        if nrwo == "PROPS":
            dic["removeg"] = False
            if not dic["edit"]:
                dic["lol"].append("EDIT\n")
                dic["lol"].append("INCLUDE")
                dic["lol"].append(f"'{dic['label']}PORV.INC' /\n")
                if dic["trans"] > 0:
                    for name in ["tranx", "trany", "tranz"]:
                        dic["lol"].append("INCLUDE")
                        dic["lol"].append(f"'{dic['label']}{name.upper()}.INC' /\n")
        elif dic["edit"]:
            if handle_editnnc(dic, nrwo):
                return True
            if handle_multiply(dic, nrwo):
                return True
        else:
            return True
    return False


def handle_multflt(dic, nrwo):
    """
    Handle the fault multipliers

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if "MULTFLT" in nrwo:
        edit = nrwo.split()
        if edit[0] != "MULTFLT":
            return False
        dic["multflt"] = True
        dic["lol"].append(edit[0])
        return True
    if dic["multflt"]:
        edit = nrwo.split()
        if edit:
            dic["lol"].append(nrwo)
            if edit[0] == "/":
                dic["multflt"] = False
        return True
    return False


def handle_mapaxes(dic, nrwo):
    """
    Keep the mapping so the grids have the same view

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if "MAPAXES" in nrwo:
        edit = nrwo.split()
        if edit[0] != "MAPAXES":
            return False
        dic["mapaxes"] = True
        dic["lol"].append(edit[0])
        return True
    if dic["mapaxes"]:
        edit = nrwo.split()
        if edit:
            dic["lol"].append(nrwo)
            if edit[-1] == "/" or edit[0] == "/":
                dic["mapaxes"] = False
        return True
    return False


def handle_multiply(dic, nrwo):
    """
    Handle the  i,j,k coarser multiply indices

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "MULTIPLY":
        dic["multiply"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["multiply"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["lol"].append(nrwo)
                dic["multiply"] = False
        if len(edit) > 2:
            if edit[0] != "--":
                edit[2] = str(dic["ic"][int(edit[2])])
                edit[3] = str(dic["ic"][int(edit[3])])
                edit[4] = str(dic["jc"][int(edit[4])])
                edit[5] = str(dic["jc"][int(edit[5])])
                edit[6] = str(dic["kc"][int(edit[6])])
                edit[7] = str(dic["kc"][int(edit[7])])
                dic["lol"].append(" ".join(edit))
                return True
    return True


def handle_editnnc(dic, nrwo):
    """
    Handle the  i,j,k coarser nnc indices

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "EDITNNC":
        dic["editnnc"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["editnnc"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["lol"].append(nrwo)
                dic["editnnc"] = False
        if len(edit) > 2:
            if edit[0] != "--":
                edit[0] = str(dic["ic"][int(edit[0])])
                edit[1] = str(dic["jc"][int(edit[1])])
                edit[2] = str(dic["kc"][int(edit[2])])
                edit[3] = str(dic["ic"][int(edit[3])])
                edit[4] = str(dic["jc"][int(edit[4])])
                edit[5] = str(dic["kc"][int(edit[5])])
                dic["lol"].append(" ".join(edit))
                return True
    return False


def handle_fault(dic, nrwo):
    """
    Handle the  i,j,k coarser fault indices

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "FAULTS":
        dic["fault"] = True
        dic["lol"].append(nrwo)
        dic["afault"] = []
        return True
    if dic["fault"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["lol"].append(nrwo)
                dic["fault"] = False
        if len(edit) > 2:
            if edit[0] != "--":
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["ic"][int(edit[2])])
                edit[3] = str(dic["jc"][int(edit[3])])
                edit[4] = str(dic["jc"][int(edit[4])])
                edit[5] = str(dic["kc"][int(edit[5])])
                edit[6] = str(dic["kc"][int(edit[6])])
                dic["lol"].append(" ".join(edit))
                return True
    return False


def handle_segmented_wells(dic, nrwo):
    """
    We also support segmented wells

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "COMPSEGS":
        dic["compsegs"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["compdat"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["compdat"] = False
        if len(edit) > 2:
            if edit[0][:2] != "--":
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["jc"][int(edit[2])])
                edit[3] = str(dic["kc"][int(edit[3])])
                edit[4] = str(dic["kc"][int(edit[4])])
                if dic["remove"] > 0 and len(edit) > 7:
                    edit[7] = "1*"
                if dic["remove"] > 0 and len(edit) > 9:
                    edit[9] = "1*"
                if dic["remove"] > 1 and len(edit) > 12:
                    edit[-2] = ""
                dic["lol"].append(" ".join(edit))
                return True
    if dic["compsegs"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["compsegs"] = False
        if len(edit) > 2:
            if edit[0][:2] != "--":
                edit[0] = str(dic["ic"][int(edit[0])])
                edit[1] = str(dic["jc"][int(edit[1])])
                edit[2] = str(dic["kc"][int(edit[2])])
                dic["lol"].append(" ".join(edit))
                return True
    return False


def handle_wells(dic, nrwo):
    """
    Add the necessary keywords and right i,j,k coarser well indices

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "WELSPECS":
        dic["welspecs"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["welspecs"]:
        edit = nrwo.split()
        if len(edit) > 2:
            if edit[0][:2] != "--":
                edit[2] = str(dic["ic"][int(edit[2])])
                edit[3] = str(dic["jc"][int(edit[3])])
                dic["lol"].append(" ".join(edit))
                return True
        if edit:
            if edit[0] == "/":
                dic["welspecs"] = False
    if nrwo == "COMPDAT":
        dic["compdat"] = True
        dic["lol"].append(nrwo)
        return True
    return False
