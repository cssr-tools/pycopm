# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911

"""
Methods to create modified (coarser, finner, submodels, transformations) OPM files.
"""

import numpy as np
import pandas as pd


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
    if not dic["coardir"]:
        dic["coardir"] = [""]


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


def handle_refinement(dic):
    """
    Create the refinement objects

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["X"] = np.zeros(dic["grid"].nx, int)
    dic["Y"] = np.zeros(dic["grid"].ny, int)
    dic["Z"] = np.zeros(dic["grid"].nz, int)
    if len(dic["rcijk"]) > 2:
        dic["X"] += dic["rcijk"][0]
        dic["Y"] += dic["rcijk"][1]
        dic["Z"] += dic["rcijk"][2]
    else:
        for i in ["x", "y", "z"]:
            if dic[f"{i}ref"]:
                dic[i.upper()] = np.array(dic[f"{i}ref"])
    dic["nx"] = dic["grid"].nx + int(sum(dic["X"]))
    dic["ny"] = dic["grid"].ny + int(sum(dic["Y"]))
    dic["nz"] = dic["grid"].nz + int(sum(dic["Z"]))


def map_ijk(dic):
    """
    Create the mappings to the new i,j,k indices

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["ic"] = np.array([0 for _ in range(dic["grid"].nx + 1)])
    dic["i1"] = np.array([0 for _ in range(dic["grid"].nx + 1)])
    dic["in"] = np.array([0 for _ in range(dic["grid"].nx + 1)])
    dic["jc"] = np.array([0 for _ in range(dic["grid"].ny + 1)])
    dic["j1"] = np.array([0 for _ in range(dic["grid"].ny + 1)])
    dic["jn"] = np.array([0 for _ in range(dic["grid"].ny + 1)])
    dic["kc"] = np.array([0 for _ in range(dic["grid"].nz + 1)])
    dic["k1"] = np.array([0 for _ in range(dic["grid"].nz + 1)])
    dic["kn"] = np.array([0 for _ in range(dic["grid"].nz + 1)])
    dic["nc"] = np.ones(dic["grid"].nx * dic["grid"].ny * dic["grid"].nz)
    if dic["refinement"]:
        for j, k in zip(["i", "j", "k"], ["X", "Y", "Z"]):
            n = 2
            for i in range(len(dic[f"{j}c"]) - 1):
                m = 1
                for l in range(dic[k][i]):
                    n += 1
                    if l % 2 == 0:
                        m += 1
                dic[f"{j}c"][i + 1] = n - m
                dic[f"{j}1"][i + 1] = n - 2 * (m - 1) - (dic[k][i] + 1) % 2
                dic[f"{j}n"][i + 1] = n - 1
                n += 1
        n = 0
        for k in range(dic["grid"].nz):
            for j in range(dic["grid"].ny):
                for i in range(dic["grid"].nx):
                    dic["nc"][n] = (
                        (dic["X"][i] + 1) * (dic["Y"][j] + 1) * (dic["Z"][k] + 1)
                    )
                    n += 1
    else:
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


def refine_grid(dic):
    """
    Refine the reservoir grid

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    crx, dic["zc"], dic["cr"] = [], [], []
    zc = list(dic["grid"].export_zcorn())
    cr = list(dic["grid"].export_coord())
    for j in range(dic["grid"].ny + 1):
        l = 6 * (dic["grid"].nx + 1) * j
        for n in range(6):
            crx.append(cr[n + l])
        for i in range(dic["grid"].nx):
            m = l + 6 * i
            for n in range(dic["X"][i] + 1):
                crx.append(cr[m] + (n + 1) * (cr[m + 6] - cr[m]) / (dic["X"][i] + 1.0))
                crx.append(
                    cr[m + 1] + (n + 1) * (cr[m + 7] - cr[m + 1]) / (dic["X"][i] + 1.0)
                )
                crx.append(
                    cr[m + 2] + (n + 1) * (cr[m + 8] - cr[m + 2]) / (dic["X"][i] + 1.0)
                )
                crx.append(
                    cr[m + 3] + (n + 1) * (cr[m + 9] - cr[m + 3]) / (dic["X"][i] + 1.0)
                )
                crx.append(
                    cr[m + 4] + (n + 1) * (cr[m + 10] - cr[m + 4]) / (dic["X"][i] + 1.0)
                )
                crx.append(
                    cr[m + 5] + (n + 1) * (cr[m + 11] - cr[m + 5]) / (dic["X"][i] + 1.0)
                )
    for i in range(dic["nx"] + 1):
        m = 6 * i
        dic["cr"].append(crx[m])
        dic["cr"].append(crx[m + 1])
        dic["cr"].append(crx[m + 2])
        dic["cr"].append(crx[m + 3])
        dic["cr"].append(crx[m + 4])
        dic["cr"].append(crx[m + 5])
    s = 6 * (dic["nx"] + 1)
    for j in range(dic["grid"].ny):
        l = 6 * (dic["nx"] + 1) * j
        for n in range(dic["Y"][j] + 1):
            for i in range(dic["nx"] + 1):
                m = l + 6 * i
                dic["cr"].append(
                    crx[m] + (n + 1) * (crx[m + s] - crx[m]) / (dic["Y"][j] + 1)
                )
                dic["cr"].append(
                    crx[m + 1]
                    + (n + 1) * (crx[m + s + 1] - crx[m + 1]) / (dic["Y"][j] + 1)
                )
                dic["cr"].append(
                    crx[m + 2]
                    + (n + 1) * (crx[m + s + 2] - crx[m + 2]) / (dic["Y"][j] + 1)
                )
                dic["cr"].append(
                    crx[m + 3]
                    + (n + 1) * (crx[m + s + 3] - crx[m + 3]) / (dic["Y"][j] + 1)
                )
                dic["cr"].append(
                    crx[m + 4]
                    + (n + 1) * (crx[m + s + 4] - crx[m + 4]) / (dic["Y"][j] + 1)
                )
                dic["cr"].append(
                    crx[m + 5]
                    + (n + 1) * (crx[m + s + 5] - crx[m + 5]) / (dic["Y"][j] + 1)
                )
    nxy = 4 * dic["grid"].nx * dic["grid"].ny
    for k in range(dic["grid"].nz):
        for o in range(2 * dic["grid"].ny):
            z_0 = []
            z_1 = []
            for l in range(2 * dic["grid"].nx):
                n = (2 * k) * nxy + o * 2 * dic["grid"].nx + l
                dic["zc"].append(zc[n])
                z_0.append(dic["zc"][-1])
                if l % 2 == 0:
                    for q in range(dic["X"][int(l / 2)]):
                        dic["zc"].append(
                            zc[n]
                            + (q + 1) * (zc[n + 1] - zc[n]) / (dic["X"][int(l / 2)] + 1)
                        )
                        z_0.append(dic["zc"][-1])
                        dic["zc"].append(
                            zc[n]
                            + (q + 1) * (zc[n + 1] - zc[n]) / (dic["X"][int(l / 2)] + 1)
                        )
                        z_0.append(dic["zc"][-1])
            if o % 2 == 0:
                for l in range(2 * dic["grid"].nx):
                    n = (2 * k) * nxy + (o + 1) * 2 * dic["grid"].nx + l
                    z_1.append(zc[n])
                    if l % 2 == 0:
                        for q in range(dic["X"][int(l / 2)]):
                            z_1.append(
                                zc[n]
                                + (q + 1)
                                * (zc[n + 1] - zc[n])
                                / (dic["X"][int(l / 2)] + 1)
                            )
                            z_1.append(
                                zc[n]
                                + (q + 1)
                                * (zc[n + 1] - zc[n])
                                / (dic["X"][int(l / 2)] + 1)
                            )
                for g in range(dic["Y"][int(o / 2)]):
                    for _ in range(2):
                        for z0, z1 in zip(z_0, z_1):
                            dic["zc"].append(
                                z0 + (g + 1) * (z1 - z0) / (dic["Y"][int(o / 2)] + 1)
                            )
        for i in range(dic["Z"][k]):
            for _ in range(2):
                for o in range(2 * dic["grid"].ny):
                    z_0 = []
                    z_1 = []
                    for l in range(2 * dic["grid"].nx):
                        n = (2 * k) * nxy + o * 2 * dic["grid"].nx + l
                        dic["zc"].append(
                            zc[n] + (i + 1) * (zc[n + nxy] - zc[n]) / (dic["Z"][k] + 1)
                        )
                        z_0.append(dic["zc"][-1])
                        if l % 2 == 0:
                            nn = n + 1
                            z_a = dic["zc"][-1]
                            z_b = zc[nn] + (i + 1) * (zc[nn + nxy] - zc[nn]) / (
                                dic["Z"][k] + 1
                            )
                            for q in range(dic["X"][int(l / 2)]):
                                dic["zc"].append(
                                    z_a
                                    + (q + 1) * (z_b - z_a) / (dic["X"][int(l / 2)] + 1)
                                )
                                z_0.append(dic["zc"][-1])
                                dic["zc"].append(
                                    z_a
                                    + (q + 1) * (z_b - z_a) / (dic["X"][int(l / 2)] + 1)
                                )
                                z_0.append(dic["zc"][-1])
                    if o % 2 == 0:
                        for l in range(2 * dic["grid"].nx):
                            n = (2 * k) * nxy + (o + 1) * 2 * dic["grid"].nx + l
                            z_1.append(
                                zc[n]
                                + (i + 1) * (zc[n + nxy] - zc[n]) / (dic["Z"][k] + 1)
                            )
                            if l % 2 == 0:
                                nn = n + 1
                                z_a = z_1[-1]
                                z_b = zc[nn] + (i + 1) * (zc[nn + nxy] - zc[nn]) / (
                                    dic["Z"][k] + 1
                                )
                                for q in range(dic["X"][int(l / 2)]):
                                    z_1.append(
                                        z_a
                                        + (q + 1)
                                        * (z_b - z_a)
                                        / (dic["X"][int(l / 2)] + 1)
                                    )
                                    z_1.append(
                                        z_a
                                        + (q + 1)
                                        * (z_b - z_a)
                                        / (dic["X"][int(l / 2)] + 1)
                                    )
                        for g in range(dic["Y"][int(o / 2)]):
                            for _ in range(2):
                                for z0, z1 in zip(z_0, z_1):
                                    dic["zc"].append(
                                        z0
                                        + (g + 1)
                                        * (z1 - z0)
                                        / (dic["Y"][int(o / 2)] + 1)
                                    )
        for o in range(2 * dic["grid"].ny):
            z_0 = []
            z_1 = []
            for l in range(2 * dic["grid"].nx):
                n = (2 * k + 1) * nxy + o * 2 * dic["grid"].nx + l
                dic["zc"].append(zc[n])
                z_0.append(dic["zc"][-1])
                if l % 2 == 0:
                    for q in range(dic["X"][int(l / 2)]):
                        dic["zc"].append(
                            zc[n]
                            + (q + 1) * (zc[n + 1] - zc[n]) / (dic["X"][int(l / 2)] + 1)
                        )
                        z_0.append(dic["zc"][-1])
                        dic["zc"].append(
                            zc[n]
                            + (q + 1) * (zc[n + 1] - zc[n]) / (dic["X"][int(l / 2)] + 1)
                        )
                        z_0.append(dic["zc"][-1])
            if o % 2 == 0:
                for l in range(2 * dic["grid"].nx):
                    n = (2 * k + 1) * nxy + (o + 1) * 2 * dic["grid"].nx + l
                    z_1.append(zc[n])
                    if l % 2 == 0:
                        for q in range(dic["X"][int(l / 2)]):
                            z_1.append(
                                zc[n]
                                + (q + 1)
                                * (zc[n + 1] - zc[n])
                                / (dic["X"][int(l / 2)] + 1)
                            )
                            z_1.append(
                                zc[n]
                                + (q + 1)
                                * (zc[n + 1] - zc[n])
                                / (dic["X"][int(l / 2)] + 1)
                            )
                for g in range(dic["Y"][int(o / 2)]):
                    for _ in range(2):
                        for z0, z1 in zip(z_0, z_1):
                            dic["zc"].append(
                                z0 + (g + 1) * (z1 - z0) / (dic["Y"][int(o / 2)] + 1)
                            )
