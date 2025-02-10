# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911

"""
Methods to create modified (coarser, finner, submodels, transformations) OPM files.
"""

import sys
import numpy as np
import pandas as pd
from shapely import Polygon, prepare, contains_xy


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
            elif name in ["poro", "swatinit", "disperc", "thconr"]:
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


def add_pv_bc(dic):
    """
    Add the pore volume from outside the submodel on the xy directions

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    for k in range(dic["nz"]):
        k_r = k + dic["mink"] - 1
        j_0 = dic["minkj"][k_r] - dic["minj"]
        i_0 = dic["minki"][k_r] - dic["mini"]
        j_n = dic["maxj"] - dic["maxkj"][k_r]
        i_n = dic["maxi"] - dic["maxki"][k_r]
        porv00 = 0
        porvi0 = 0
        porv0j = 0
        porvij = 0
        pvs = 0
        pvn = 0
        pve = 0
        pvw = 0
        nums = 0
        numn = 0
        nume = 0
        numw = 0
        ijs = [0] * dic["nx"]
        ijn = [0] * dic["nx"]
        ije = [0] * dic["ny"]
        ijw = [0] * dic["ny"]
        inb = 0
        for j in range(dic["minkj"][k_r] - 1):
            for i in range(dic["minki"][k_r] - 1):
                ind = (
                    i
                    + j * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                porv00 += dic["porv"][ind]
        for j in range(dic["grid"].ny - dic["maxkj"][k_r]):
            for i in range(dic["minki"][k_r] - 1):
                ind = (
                    i
                    + (j + dic["maxkj"][k_r]) * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                porv0j += dic["porv"][ind]
        for j in range(dic["minkj"][k_r] - 1):
            for i in range(dic["grid"].nx - dic["maxki"][k_r]):
                ind = (
                    i
                    + dic["maxki"][k_r]
                    + j * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                porvi0 += dic["porv"][ind]
        for j in range(dic["grid"].ny - dic["maxkj"][k_r]):
            for i in range(dic["grid"].nx - dic["maxki"][k_r]):
                ind = (
                    i
                    + dic["maxki"][k_r]
                    + (j + dic["maxkj"][k_r]) * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                porvij += dic["porv"][ind]
        for i in range(dic["nx"] - i_0 - i_n):
            ins = i + i_0 + j_0 * dic["nx"] + k * dic["nx"] * dic["ny"]
            ind = (i + dic["minki"][k_r] - 1) + (k + dic["mink"] - 1) * dic[
                "grid"
            ].nx * dic["grid"].ny
            pvy = 0
            for j in range(dic["minkj"][k_r] - 1):
                ind = (
                    (i + dic["minki"][k_r] - 1)
                    + j * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                pvy += dic["porv"][ind]
            if int(dic["actnum_c"][ins]) > 0:
                nums += 1.0
                if dic["pvcorr"] in [1, 2]:
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvy)
                else:
                    pvs += pvy
            elif dic["porv"][ind + 1] > 0:
                for j in range(dic["ny"] - 1 - j_0):
                    ins = (
                        i + i_0 + (j + 1 + j_0) * dic["nx"] + k * dic["nx"] * dic["ny"]
                    )
                    ind = (
                        (i + dic["minki"][k_r] - 1)
                        + (j + dic["minkj"][k_r] - 1) * dic["grid"].nx
                        + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                    )
                    pvy += 0.5 * dic["porv"][ind]
                    if int(dic["actnum_c"][ins]) > 0:
                        ijs[i] = j + 1
                        nums += 1.0
                        if dic["pvcorr"] in [1, 2]:
                            dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvy)
                        else:
                            pvs += pvy
                        break
                    if j == dic["ny"] - 2 - j_0:
                        pvs += pvy
                        break
            else:
                pvs += pvy
            ins = (
                i + i_0 + (dic["ny"] - 1 - j_n) * dic["nx"] + k * dic["nx"] * dic["ny"]
            )
            pvy = 0
            for j in range(dic["grid"].ny - dic["maxkj"][k_r]):
                ind = (
                    (i + dic["minki"][k_r] - 1)
                    + (j + dic["maxkj"][k_r]) * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                if j == 0:
                    inb = ind - dic["grid"].nx
                pvy += dic["porv"][ind]
            if int(dic["actnum_c"][ins]) > 0:
                numn += 1.0
                if dic["pvcorr"] in [1, 2]:
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvy)
                else:
                    pvn += pvy
            elif dic["porv"][inb] > 0:
                for j in range(dic["ny"] - 1 - j_n):
                    ins = (
                        i
                        + i_0
                        + (dic["ny"] - 2 - j - j_n) * dic["nx"]
                        + k * dic["nx"] * dic["ny"]
                    )
                    ind = (
                        (i + dic["minki"][k_r] - 1)
                        + (dic["maxkj"][k_r] - j - 1) * dic["grid"].nx
                        + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                    )
                    pvy += 0.5 * dic["porv"][ind]
                    if int(dic["actnum_c"][ins]) > 0:
                        ijn[i] = j + 1
                        numn += 1.0
                        if dic["pvcorr"] in [1, 2]:
                            dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvy)
                        else:
                            pvn += pvy
                        break
                    if j == dic["ny"] - 2 - j_n:
                        pvn += pvy
                        break
            else:
                pvn += pvy
        for j in range(dic["ny"] - j_0 - j_n):
            ins = i_0 + (j + j_0) * dic["nx"] + k * dic["nx"] * dic["ny"]
            pvx = 0
            for i in range(dic["minki"][k_r] - 1):
                ind = (
                    i
                    + (j + dic["minkj"][k_r] - 1) * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                pvx += dic["porv"][ind]
            if int(dic["actnum_c"][ins]) > 0:
                nume += 1.0
                if dic["pvcorr"] in [1, 2]:
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvx)
                else:
                    pve += pvx
            elif dic["porv"][ind + 1] > 0:
                for i in range(dic["nx"] - 1 - i_0):
                    ins = (
                        i + i_0 + 1 + (j + j_0) * dic["nx"] + k * dic["nx"] * dic["ny"]
                    )
                    ind = (
                        (i + dic["minki"][k_r] - 1)
                        + (j + dic["minkj"][k_r] - 1) * dic["grid"].nx
                        + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                    )
                    pvx += 0.5 * dic["porv"][ind]
                    if int(dic["actnum_c"][ins]) > 0:
                        ije[j] = i + 1
                        nume += 1.0
                        if dic["pvcorr"] in [1, 2]:
                            dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvx)
                        else:
                            pve += pvx
                        break
                    if i == dic["nx"] - 2 - i_0:
                        pve += pvx
                        break
            else:
                pve += pvx
            ins = (
                dic["nx"] - 1 - i_n + (j + j_0) * dic["nx"] + k * dic["nx"] * dic["ny"]
            )
            pvx = 0
            for i in range(dic["grid"].nx - dic["maxki"][k_r]):
                ind = (
                    (i + dic["maxki"][k_r])
                    + (j + dic["minkj"][k_r] - 1) * dic["grid"].nx
                    + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                )
                if i == 0:
                    inb = ind - 1
                pvx += dic["porv"][ind]
            if int(dic["actnum_c"][ins]) > 0:
                numw += 1.0
                if dic["pvcorr"] in [1, 2]:
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvx)
                else:
                    pvw += pvx
            elif dic["porv"][inb] > 0:
                for i in range(dic["nx"] - 1 - i_n):
                    ins = (
                        dic["nx"]
                        - 2
                        - i
                        - i_n
                        + (j + j_0) * dic["nx"]
                        + k * dic["nx"] * dic["ny"]
                    )
                    ind = (
                        (dic["maxki"][k_r] - 1 - i)
                        + (j + dic["minkj"][k_r] - 1) * dic["grid"].nx
                        + (k + dic["mink"] - 1) * dic["grid"].nx * dic["grid"].ny
                    )
                    pvx += 0.5 * dic["porv"][ind]
                    if int(dic["actnum_c"][ins]) > 0:
                        ijw[j] = i + 1
                        numw += 1.0
                        if dic["pvcorr"] in [1, 2]:
                            dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pvx)
                        else:
                            pvw += pvx
                        break
                    if i == dic["nx"] - 2 - i_n:
                        pvw += pvx
                        break
            else:
                pvw += pvx
        if dic["pvcorr"] == 4:
            if dic["freqsub"][k] > 0:
                totpv = (
                    pvs + pvn + pve + pvw + porv00 + porvi0 + porv0j + porvij
                ) / dic["freqsub"][k]
                for i in range(
                    k * dic["nx"] * dic["ny"], (k + 1) * dic["nx"] * dic["ny"]
                ):
                    if int(dic["actnum_c"][i]) > 0:
                        dic["porv_c"][i] = str(float(dic["porv_c"][i]) + totpv)
        else:
            for i in range(dic["nx"] - i_0 - i_n):
                ins = i + i_0 + (ijs[i] + j_0) * dic["nx"] + k * dic["nx"] * dic["ny"]
                pva = 0
                if int(dic["actnum_c"][ins]) > 0:
                    if nums > 0:
                        pva += pvs / nums
                        if dic["pvcorr"] in [1, 3]:
                            pva += porv00 / (nums + nume)
                            pva += porvi0 / (nums + numw)
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pva)
                ins = (
                    i
                    + i_0
                    + (dic["ny"] - 1 - ijn[i] - j_n) * dic["nx"]
                    + k * dic["nx"] * dic["ny"]
                )
                pva = 0
                if int(dic["actnum_c"][ins]) > 0:
                    if numn > 0:
                        pva += pvn / numn
                        if dic["pvcorr"] in [1, 3]:
                            pva += porv0j / (numn + nume)
                            pva += porvij / (numn + numw)
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pva)
            for j in range(dic["ny"] - j_0 - j_n):
                ins = ije[j] + i_0 + (j + j_0) * dic["nx"] + k * dic["nx"] * dic["ny"]
                pva = 0
                if int(dic["actnum_c"][ins]) > 0:
                    if nume > 0:
                        pva += pve / nume
                        if dic["pvcorr"] in [1, 3]:
                            pva += porv00 / (nume + nums)
                            pva += porv0j / (nume + numn)
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pva)
                ins = (
                    dic["nx"]
                    - 1
                    - ijw[j]
                    - i_n
                    + (j + j_0) * dic["nx"]
                    + k * dic["nx"] * dic["ny"]
                )
                pva = 0
                if int(dic["actnum_c"][ins]) > 0:
                    if numw > 0:
                        pva += pvw / numw
                        if dic["pvcorr"] in [1, 3]:
                            pva += porvi0 / (numw + nums)
                            pva += porvij / (numw + numn)
                    dic["porv_c"][ins] = str(float(dic["porv_c"][ins]) + pva)
            if dic["pvcorr"] == 2:
                dic["porv_c"][0] = str(float(dic["porv_c"][0]) + porv00)
                dic["porv_c"][dic["nx"] - 1] = str(
                    float(dic["porv_c"][dic["nx"] - 1]) + porvi0
                )
                dic["porv_c"][(dic["ny"] - 1) * dic["nx"]] = str(
                    float(dic["porv_c"][(dic["ny"] - 1) * dic["nx"]]) + porv0j
                )
                dic["porv_c"][-1] = str(float(dic["porv_c"][-1]) + porvij)


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
                size = len(dic[f"{i}coar"])
                dic[i.upper()][:size] = np.array(dic[f"{i}coar"])
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


def handle_vicinity(dic):
    """
    Create the vicinity objects

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    vicinity = dic["vicinity"].split(" ")
    quan = vicinity[0].upper()
    if quan == "XYPOLYGON":
        coords = dic["grid"].export_position(dic["grid"].export_index())
        nxy = dic["grid"].nx * dic["grid"].ny
        nxyz = nxy * dic["grid"].nz
        dic["subm"] = []
        poly = np.array(
            [
                [float(x.split(",")[0][1:]), float(x.split(",")[1][:-1])]
                for x in vicinity[1:]
            ]
        )
        npoly = len(poly)
        minpp = poly.min(axis=0)
        maxpp = poly.max(axis=0)
        pts = coords[:nxy][:, 0:2]
        minx = pts.min(axis=0)
        maxx = pts.max(axis=0)
        minx = np.array([min(minx[0], minpp[0]), min(minx[1], minpp[1])])
        maxx = np.array([max(maxx[0], maxpp[0]), max(maxx[1], maxpp[1])])
        for k in range(dic["grid"].nz - 1):
            pts = coords[(k + 1) * nxy : (k + 2) * nxy][:, 0:2]
            minx = np.array(
                [min(minx[0], pts.min(axis=0)[0]), min(minx[1], pts.min(axis=0)[1])]
            )
            maxx = np.array(
                [max(maxx[0], pts.max(axis=0)[0]), max(maxx[1], pts.max(axis=0)[1])]
            )
        minp = np.array(list([minx]) * nxyz)
        maxp = np.array(list([maxx]) * nxyz)
        nrmp = (coords[:][:, 0:2] - minp) / (maxp - minp)
        minp = np.array(list([minx]) * npoly)
        maxp = np.array(list([maxx]) * npoly)
        poly = (poly - minp) / (maxp - minp)
        area = Polygon(poly)
        prepare(area)
        dic["subm"] = contains_xy(area, nrmp[:, 0], nrmp[:, 1])
    else:
        if dic["ini"].has_kw(quan):
            dic["subm"] = np.ones(dic["grid"].nx * dic["grid"].ny * dic["grid"].nz)
            dic["subm"][dic["actind"]] = dic["ini"].iget_kw(quan)[0]
            quans = [int(val) for val in vicinity[1].split(",")]
            dic["subm"] = [val in quans for val in dic["subm"]]
        else:
            print(
                f"\nThe simulation model does not have the keyword {quan}, "
                "add the keyword to the deck or use 'xypolygon'."
            )
            sys.exit()
    nxy = dic["grid"].nx * dic["grid"].ny
    dic["mini"] = dic["grid"].nx
    dic["maxi"] = 1
    dic["minj"] = dic["grid"].ny
    dic["maxj"] = 1
    dic["mink"] = dic["grid"].nz
    dic["maxk"] = 1
    dic["minki"] = [dic["grid"].nx] * dic["grid"].nz
    dic["maxki"] = [1] * dic["grid"].nz
    dic["minkj"] = [dic["grid"].ny] * dic["grid"].nz
    dic["maxkj"] = [1] * dic["grid"].nz
    for k in range(dic["grid"].nz):
        for j in range(dic["grid"].ny):
            for i in range(dic["grid"].nx):
                ind = i + j * dic["grid"].nx + k * dic["grid"].nx * dic["grid"].ny
                if dic["subm"][ind] and dic["porv"][ind] > 0:
                    dic["mini"] = min(dic["mini"], i + 1)
                    dic["minj"] = min(dic["minj"], j + 1)
                    dic["mink"] = min(dic["mink"], k + 1)
                    dic["maxi"] = max(dic["maxi"], i + 1)
                    dic["maxj"] = max(dic["maxj"], j + 1)
                    dic["maxk"] = max(dic["maxk"], k + 1)
                    dic["minki"][k] = min(dic["minki"][k], i + 1)
                    dic["minkj"][k] = min(dic["minkj"][k], j + 1)
                    dic["maxki"][k] = max(dic["maxki"][k], i + 1)
                    dic["maxkj"][k] = max(dic["maxkj"][k], j + 1)


def map_vicinity(dic):
    """
    Properties to the vicinity

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    nc = dic["grid"].nx * dic["grid"].ny * dic["grid"].nz
    dic["actind"] = dic["porv"] > 0
    dic["freqsub"] = [0.0] * dic["nz"]
    for name in dic["props"] + dic["regions"] + dic["grids"] + ["porv"]:
        if name != "porv":
            dic[name] = np.zeros(nc)
            dic[name][dic["actind"]] = dic["ini"].iget_kw(name.upper())[0]
        dic[f"{name}_c"] = [""] * (dic["nx"] * dic["ny"] * dic["nz"])
        n = 0
        for k in range(dic["grid"].nz):
            for j in range(dic["grid"].ny):
                for i in range(dic["grid"].nx):
                    ind = i + j * dic["grid"].nx + k * dic["grid"].nx * dic["grid"].ny
                    if (
                        dic["mini"] <= i + 1
                        and i + 1 <= dic["maxi"]
                        and dic["minj"] <= j + 1
                        and j + 1 <= dic["maxj"]
                        and dic["mink"] <= k + 1
                        and k + 1 <= dic["maxk"]
                    ):
                        if dic["actind"][ind] and dic["subm"][ind]:
                            dic[f"{name}_c"][n] = str(
                                int(dic[name][ind]) if "num" in name else dic[name][ind]
                            )
                            if name == "porv":
                                dic["freqsub"][k + 1 - dic["mink"]] += 1.0
                        else:
                            dic[f"{name}_c"][n] = "0"
                        n += 1
    dic["actnum_c"] = ["1" if float(val) > 0 else "0" for val in dic["porv_c"]]


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
    elif dic["vicinity"]:
        n = 1
        m = 1
        for i in range(dic["grid"].nx):
            if dic["mini"] <= i + 1 and i + 1 <= dic["maxi"]:
                dic["ic"][n] = m
                m += 1
            n += 1
        dic["nx"] = m - 1
        n = 1
        m = 1
        for j in range(dic["grid"].ny):
            if dic["minj"] <= j + 1 and j + 1 <= dic["maxj"]:
                dic["jc"][n] = m
                m += 1
            n += 1
        dic["ny"] = m - 1
        n = 1
        m = 1
        for k in range(dic["grid"].nz):
            if dic["mink"] <= k + 1 and k + 1 <= dic["maxk"]:
                dic["kc"][n] = m
                m += 1
            n += 1
        dic["nz"] = m - 1
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


def chop_grid(dic):
    """
    Extract the corresponding subgrid

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["zc"], dic["cr"] = [], []
    zc = list(dic["grid"].export_zcorn())
    cr = list(dic["grid"].export_coord())
    for j in range(dic["grid"].ny + 1):
        l = 6 * (dic["grid"].nx + 1) * j
        added = False
        for i in range(dic["grid"].nx):
            m = l + 6 * i
            if (
                dic["mini"] <= i + 1
                and i + 1 <= dic["maxi"]
                and dic["minj"] <= j + 1
                and j <= dic["maxj"]
            ):
                if added:
                    for n in range(6):
                        dic["cr"].append(cr[n + m + 6])
                else:
                    added = True
                    for n in range(12):
                        dic["cr"].append(cr[n + m])
            else:
                added = False
    nxy = 4 * dic["grid"].nx * dic["grid"].ny
    for k in range(dic["grid"].nz):
        if (dic["kc"][k + 1]) > 0:
            for l in range(2):
                for j in range(2 * dic["grid"].ny):
                    for i in range(2 * dic["grid"].nx):
                        n = (l + 2 * k) * nxy + j * 2 * dic["grid"].nx + i
                        if (
                            dic["ic"][int(i / 2) + 1] > 0
                            and dic["jc"][int(j / 2) + 1] > 0
                        ):
                            dic["zc"].append(zc[n])


def transform_grid(dic):
    """
    Transform the reservoir grid

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["zc"], dic["cr"] = [], []
    cxy = []
    trans = dic["transform"].split(" ")
    if trans[0] in ["translate", "scale"]:
        txyz = trans[1].split(",")
        txyz = np.array([float(txyz[0][1:]), float(txyz[1]), float(txyz[-1][:-1])])
    else:
        txyz = float(trans[1])
    zc = list(dic["grid"].export_zcorn())
    cr = list(dic["grid"].export_coord())
    if trans[0] in ["rotatexz", "rotateyz"]:
        xyz = dic["grid"].export_corners(dic["grid"].export_index())
        for k in range(dic["grid"].nz):
            for j in range(dic["grid"].ny):
                for i in range(dic["grid"].nx):
                    ind = i + j * dic["grid"].nx + k * dic["grid"].nx * dic["grid"].ny
                    cxy.append([xyz[ind][0], xyz[ind][1]])
                    cxy.append([xyz[ind][3], xyz[ind][4]])
                for i in range(dic["grid"].nx):
                    ind = i + j * dic["grid"].nx + k * dic["grid"].nx * dic["grid"].ny
                    cxy.append([xyz[ind][6], xyz[ind][7]])
                    cxy.append([xyz[ind][9], xyz[ind][10]])
            for j in range(dic["grid"].ny):
                for i in range(dic["grid"].nx):
                    ind = i + j * dic["grid"].nx + k * dic["grid"].nx * dic["grid"].ny
                    cxy.append([xyz[ind][12], xyz[ind][13]])
                    cxy.append([xyz[ind][15], xyz[ind][16]])
                for i in range(dic["grid"].nx):
                    ind = i + j * dic["grid"].nx + k * dic["grid"].nx * dic["grid"].ny
                    cxy.append([xyz[ind][18], xyz[ind][19]])
                    cxy.append([xyz[ind][21], xyz[ind][22]])
    for j in range(dic["grid"].ny + 1):
        l = 6 * (dic["grid"].nx + 1) * j
        for i in range(dic["grid"].nx + 1):
            m = l + 6 * i
            if trans[0] == "translate":
                for n in range(6):
                    dic["cr"].append(cr[m + n] + txyz[n % 3])
            elif trans[0] == "scale":
                for n in range(6):
                    dic["cr"].append(cr[m + n] * txyz[n % 3])
            else:
                if trans[0] == "rotatexy":
                    for n in range(2):
                        dic["cr"].append(
                            cr[m + 3 * n] * np.cos(txyz * np.pi / 180)
                            - cr[m + 3 * n + 1] * np.sin(txyz * np.pi / 180)
                        )
                        dic["cr"].append(
                            cr[m + 3 * n + 1] * np.cos(txyz * np.pi / 180)
                            + cr[m + 3 * n] * np.sin(txyz * np.pi / 180)
                        )
                        dic["cr"].append(cr[m + 3 * n + 2])
                elif trans[0] == "rotatexz":
                    for n in range(2):
                        dic["cr"].append(
                            cr[m + 3 * n] * np.cos(txyz * np.pi / 180)
                            + cr[m + 3 * n + 2] * np.sin(txyz * np.pi / 180)
                        )
                        dic["cr"].append(cr[m + 3 * n + 1])
                        dic["cr"].append(
                            cr[m + 3 * n + 2] * np.cos(txyz * np.pi / 180)
                            - cr[m + 3 * n] * np.sin(txyz * np.pi / 180)
                        )
                else:
                    for n in range(2):
                        dic["cr"].append(cr[m + 3 * n])
                        dic["cr"].append(
                            cr[m + 3 * n + 1] * np.cos(txyz * np.pi / 180)
                            - cr[m + 3 * n + 2] * np.sin(txyz * np.pi / 180)
                        )
                        dic["cr"].append(
                            cr[m + 3 * n + 2] * np.cos(txyz * np.pi / 180)
                            + cr[m + 3 * n + 1] * np.sin(txyz * np.pi / 180)
                        )
    for i, val in enumerate(zc):
        if trans[0] == "translate":
            dic["zc"].append(val + txyz[2])
        elif trans[0] == "scale":
            dic["zc"].append(val * txyz[2])
        else:
            if trans[0] == "rotatexz":
                dic["zc"].append(
                    val * np.cos(txyz * np.pi / 180)
                    - cxy[i][0] * np.sin(txyz * np.pi / 180)
                )
            elif trans[0] == "rotateyz":
                dic["zc"].append(
                    val * np.cos(txyz * np.pi / 180)
                    + cxy[i][1] * np.sin(txyz * np.pi / 180)
                )
            else:
                dic["zc"].append(val)


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
