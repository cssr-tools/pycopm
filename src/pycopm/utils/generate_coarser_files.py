# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915

"""
Utiliy methods to only create the coarser files by pycopm.
"""

import os
import csv
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
    dic["flags"] = "--parsing-strictness=low --enable-dry-run=true"
    os.system(f"{dic['flow']} {dic['deck'].upper()}.DATA {dic['flags']} & wait\n")

    # Read the data
    dic["field"] = "generic"
    dic["props"] = ["poro", "permx", "permy", "permz"]
    dic["regions"] = []
    dic["grids"] = []
    dic["grid"] = Grid(f"{dic['exe']}/" + dic["deck"] + ".EGRID")
    dic["ini"] = ResdataFile(f"{dic['exe']}/" + dic["deck"] + ".INIT")
    if dic["ini"].has_kw("SWATINIT"):
        dic["props"] += ["swatinit"]
    if dic["ini"].has_kw("MULTNUM"):
        dic["grids"] += ["multnum"]
    for name in ["satnum", "eqlnum", "fipnum", "pvtnum", "imbnum"]:
        if dic["ini"].has_kw(name.upper()):
            if max(dic["ini"].iget_kw(name.upper())[0]) > 1:
                dic["regions"] += [name]
    nc = dic["grid"].nx * dic["grid"].ny * dic["grid"].nz
    dic["con"] = np.array([0 for _ in range(nc)])
    dic["porv"] = np.array(dic["ini"].iget_kw("PORV")[0])
    actnum = np.array([0 for _ in range(nc)])
    d_z = np.array([np.nan for _ in range(nc)])
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
        actnum[cell.global_index] = cell.active
        z_t[cell.global_index] = min(cxyz[cell.global_index][i] for i in zti)
        z_b[cell.global_index] = max(cxyz[cell.global_index][i] for i in zti)
        tmp = max(cxyz[cell.global_index][i] for i in zbi)
        z_b_t[cell.global_index] = tmp - z_t[cell.global_index]
        if cell.active == 1:
            d_z[cell.global_index] = dic["grid"].cell_dz(ijk=(cell.i, cell.j, cell.k))
            for name in dic["props"] + dic["regions"] + dic["grids"]:
                dic[name][cell.global_index] = dic["ini"].iget_kw(name.upper())[0][n]
            if not dic["show"]:
                dic["permx"][cell.global_index] = (
                    dic["ini"].iget_kw("PERMX")[0][n] * d_z[cell.global_index]
                )
                dic["permy"][cell.global_index] = (
                    dic["ini"].iget_kw("PERMY")[0][n] * d_z[cell.global_index]
                )
                if dic["ini"].iget_kw("PERMZ")[0][n] != 0:
                    dic["permz"][cell.global_index] = (
                        d_z[cell.global_index] / dic["ini"].iget_kw("PERMZ")[0][n]
                    )
            n += 1

    # Coarsening
    handle_clusters(dic)
    map_ijk(dic)
    clusmin, clusmax, rmv = map_properties(dic, actnum, d_z, z_t, z_b, z_b_t)
    if dic["pvcorr"] == 1:
        handle_pv(dic, clusmin, clusmax, rmv)
    handle_cp_grid(dic)
    write_grid(dic)
    write_props(dic)
    process_the_deck(dic)
    with open(
        f"{dic['exe']}/{dic['fol']}/{dic['deck'].upper()}_PYCOPM.DATA",
        "w",
        encoding="utf8",
    ) as file:
        for row in dic["lol"]:
            file.write(row + "\n")
    # os.chdir(dic["fol"])
    # os.system(
    #     f"{dic['flow']} {dic['deck'].upper()}_PYCOPM.DATA --enable-dry-run=1 & wait\n"
    # )


def map_properties(dic, actnum, d_z, z_t, z_b, z_b_t):
    """
    Mapping to the coarse properties

    Args:
        dic (dict): Global dictionary\n
        actnum (array): Integers with the active cells\n
        d_z (array): Floats with the corresponding grid DZ\n
        z_t (array): Floats with the top cell z-center position\n
        z_b (array): Floats with the bottom cell z-center position

    Returns:
        dic (dict): Modified global dictionary

    """
    clusmax = pd.Series(actnum).groupby(dic["con"]).max()
    freq = pd.Series(actnum).groupby(dic["con"]).sum()
    dz_c = pd.Series(z_b_t).groupby(dic["con"]).max()
    h_tot = pd.Series(d_z).groupby(dic["con"]).sum()
    if dic["how"] == "min":
        clusmin = pd.Series(actnum).groupby(dic["con"]).min()
        clust = clusmin
    elif dic["how"] == "mode":
        clusmin = (
            pd.Series(actnum)
            .groupby(dic["con"])
            .agg(lambda x: pd.Series.mode(x).iat[0])
        )
        clust = clusmin
    else:
        clusmin = clusmax
        clust = clusmax
    if dic["jump"]:
        rmv = 1 * (
            (
                pd.Series(z_b).groupby(dic["con"]).max()
                - pd.Series(z_t).groupby(dic["con"]).min()
            )
            < float(dic["jump"]) * dz_c
        )
        dic["actnum_c"] = [int(val * r_m) for val, r_m in zip(clust, rmv)]
    else:
        rmv = 0 * dz_c + 1
        dic["actnum_c"] = [int(val) for val in clust]
    c_c = pd.Series(dic["porv"]).groupby(dic["con"]).sum()
    dic["porv_c"] = [f"{val}" for val in c_c]
    for name in dic["props"]:
        if not dic["show"]:
            if name in ["permx", "permy"]:
                c_c = pd.Series(dic[name]).groupby(dic["con"]).sum()
                dic[f"{name}_c"] = [
                    f"{val/h_t}" if h_t * val > 0 else "0"
                    for val, h_t in zip(c_c, h_tot)
                ]
            elif name == "permz":
                c_c = pd.Series(dic[name]).groupby(dic["con"]).sum()
                dic["permz_c"] = [
                    f"{h_t/val}" if h_t * val > 0 else "0"
                    for val, h_t in zip(c_c, h_tot)
                ]
            else:
                c_c = pd.Series(dic[name]).groupby(dic["con"]).sum()
                dic[f"{name}_c"] = [
                    f"{val/fre}" if fre > 0 else "0" for val, fre in zip(c_c, freq)
                ]
        else:
            if dic["show"] == "min":
                c_c = pd.Series(dic[name]).groupby(dic["con"]).min()
                dic[f"{name}_c"] = [f"{val}" for val in c_c]
            elif dic["show"] == "max":
                c_c = pd.Series(dic[name]).groupby(dic["con"]).max()
                dic[f"{name}_c"] = [f"{val}" for val in c_c]
            else:
                c_c = pd.Series(dic[name]).groupby(dic["con"]).sum()
                dic[f"{name}_c"] = [
                    f"{val/fre}" if fre > 0 else "0" for val, fre in zip(c_c, freq)
                ]
    for name in dic["regions"] + dic["grids"]:
        if dic["nhow"] == "min":
            c_c = pd.Series(dic[name]).groupby(dic["con"]).min()
        elif dic["nhow"] == "max":
            c_c = pd.Series(dic[name]).groupby(dic["con"]).max()
        else:
            c_c = (
                pd.Series(dic[name])
                .groupby(dic["con"])
                .agg(
                    lambda x: (
                        pd.Series.mode(x).iat[0]
                        if len(pd.Series.mode(x)) > 1
                        else pd.Series.mode(x)
                    )
                )
            )
        dic[f"{name}_c"] = [f"{int(val)}" if np.isscalar(val) else "0" for val in c_c]
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
            for prop in [
                "PORO",
                "PERM",
                "TOPS",
                "PHI",
                "FIPNUM",
                "SATNUM",
                "NTG",
                "GRID",
                "PORV",
            ]:
                if prop in file:
                    copy = False
            if copy:
                os.system(f"scp -r {dic['exe']}/{file} {dic['exe']}/{dic['fol']}")
    var = {"dic": dic}
    mytemplate = Template(filename=f"{dic['pat']}/template_scripts/common/grid.mako")
    filledtemplate = mytemplate.render(**var)
    with open(f"{dic['exe']}/{dic['fol']}/GRID.INC", "w", encoding="utf8") as f:
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
            f"{dic['exe']}/{dic['fol']}/{name.upper()}.INC",
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
    dic["lol"] = []
    dic["dimens"] = False
    dic["removeg"] = False
    dic["welspecs"] = False
    dic["compdat"] = False
    dic["compsegs"] = False
    dic["mapaxes"] = False
    dic["region"] = False
    dic["fault"] = False
    with open(dic["deck"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            if 0 < nrwo.find("\\t"):
                nrwo = nrwo.replace("\\t", " ")
            if nrwo == "DIMENS":
                dic["dimens"] = True
                continue
            if dic["dimens"]:
                if "/" in nrwo:
                    dic["dimens"] = False
                continue
            if handle_grid_props(dic, nrwo):
                continue
            if handle_regions(dic, nrwo):
                continue
            if handle_wells(dic, nrwo):
                continue
            if handle_segmented_wells(dic, nrwo):
                continue
            dic["lol"].append(nrwo)


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
                dic["lol"].append(f"'{name.upper()}.INC' /\n")
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
        dic["lol"].append("INCLUDE")
        dic["lol"].append("'GRID.INC' /\n")
        for name in dic["grids"]:
            dic["lol"].append("INCLUDE")
            dic["lol"].append(f"'{name.upper()}.INC' /\n")
        return True
    if dic["removeg"]:
        if handle_fault(dic, nrwo):
            return True
        if handle_mapaxes(dic, nrwo):
            return True
        if nrwo == "PROPS":
            dic["removeg"] = False
            dic["lol"].append("EDIT\n")
            dic["lol"].append("INCLUDE")
            dic["lol"].append("'PORV.INC' /\n")
        else:
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
    if nrwo == "MAPAXES":
        dic["mapaxes"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["mapaxes"]:
        edit = nrwo.split()
        if edit:
            dic["lol"].append(nrwo)
            if edit[-1] == "/" or edit[0] == "/":
                dic["mapaxes"] = False
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
