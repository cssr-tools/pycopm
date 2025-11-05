# SPDX-FileCopyrightText: 2024-2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=E1102

"""
Utiliy functions to generate model properties from toml configuration files.
"""

import numpy as np
from alive_progress import alive_bar


def initialize_properties(dic):
    """
    Method to initialize the coarser properties

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    names = ["poro", "porv", "vol", "permx", "permy", "permz", "ntg", "fipzon"]
    names += ["swl", "sgu", "swcr", "fluxnum", "fipnum", "eqlnum", "pvtnum"]
    names += ["swat", "sgas", "pressure", "rs", "rv", "multz", "multnum"]
    for name in names:
        dic[f"{name}_c"] = [0.0 for _ in range(dic["num_cells"])]
    dic["actnum_c"] = [0 for _ in range(dic["num_cells"])]
    dic["index"] = [[] for _ in range(dic["num_cells"])]
    dic["satnum_c"] = [1 for _ in range(dic["num_cells"])]
    for name in ["permx", "permy", "permz"]:
        dic[name + "_c_min_max"] = [[0.0, 0.0] for _ in range(dic["num_cells"])]


def coarser_properties(dic):
    """
    Method to coarse the properties defined in the input deck

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    initialize_properties(dic)
    actnum_m = [0 for _ in range(dic["num_cells"])]
    print("Coarsening the static properties")
    with alive_bar(dic["num_cells"]) as bar_animation:
        for num in range(dic["num_cells"]):
            bar_animation()
            inx = np.where(dic["con"] == num + 1)
            dic["actnum_c"][num] = int(min(dic["actnum"][inx]))
            actnum_m[num] = int(max(dic["actnum"][inx]))
            dic["fluxnum_c"][num] = int(min(dic["fluxnum"][inx]))
            dic["fipnum_c"][num] = int(min(dic["fipnum"][inx]))
            dic["eqlnum_c"][num] = int(min(dic["eqlnum"][inx]))
            dic["vol_c"][num] = sum(dic["vol"][inx])
            if dic["field"] == "drogon":
                dic["multnum_c"][num] = int(min(dic["multnum"][inx]))
                dic["pvtnum_c"][num] = int(min(dic["pvtnum"][inx]))
                dic["fipzon_c"][num] = int(min(dic["fipzon"][inx]))
                dic["satnum_c"][num] = int(min(dic["satnum"][inx]))
            if dic["deck"] == 1 and (dic["letsatn"] == 1 or dic["letsatn"] == 3):
                dic["satnum_c"][num] = int(min(dic["satnum"][inx]))
            if dic["deck"] == 1 and dic["letsatn"] == 2:
                if sum(dic["actnum_c"][0:num]) > 1:
                    dic["satnum_c"][num] += int(sum(dic["actnum_c"][0:num])) - 1

            if sum(dic["actnum"][inx]) > 0:
                dic["poro_c"][num] = (
                    sum(dic["poro"][inx] * dic["vol"][inx] * dic["actnum"][inx])
                    / dic["vol_c"][num]
                )
                for i, name in zip(range(3), ["permx", "permy", "permz"]):
                    if dic["rock"][i][2] == "max":
                        dic[name + "_c"][num] = max(dic[name][inx])
                    else:
                        dic[name + "_c"][num] = (
                            sum(dic[name][inx] * dic["vol"][inx] * dic["actnum"][inx])
                            / dic["vol_c"][num]
                        )
                dic["ntg_c"][num] = (
                    sum(dic["ntg"][inx] * dic["vol"][inx] * dic["actnum"][inx])
                    / dic["vol_c"][num]
                )
                pv_f = (
                    dic["poro"][inx]
                    * dic["vol"][inx]
                    * dic["actnum"][inx]
                    * dic["ntg"][inx]
                )
                pv_c = sum(pv_f)
                dic["porv_c"][num] = pv_c
                dic["swl_c"][num] = sum(dic["swl"][inx] * pv_f) / pv_c
                dic["sgu_c"][num] = sum(dic["sgu"][inx] * pv_f) / pv_c
                dic["swcr_c"][num] = sum(dic["swcr"][inx] * pv_f) / pv_c
                dic["swat_c"][num] = sum(dic["swat"][inx] * pv_f) / pv_c
                dic["sgas_c"][num] = sum(dic["sgas"][inx] * pv_f) / pv_c
                dic["pressure_c"][num] = sum(dic["pressure"][inx] * pv_f) / pv_c
                dic["rs_c"][num] = sum(dic["rs"][inx] * pv_f) / pv_c
                dic["rv_c"][num] = sum(dic["rv"][inx] * pv_f) / pv_c
                dic["multz_c"][num] = min(dic["multz"][inx])
            for name in ["permx", "permy", "permz"]:
                dic[name + "_c_min_max"][num] = [
                    min(dic[name][inx]),
                    1.1 * max(dic[name][inx]),
                ]
            if (actnum_m[num] - dic["actnum_c"][num]) > 0 and dic["cporv"] == 1:
                add_lost_pv_to_boundary_cells(dic, inx, num)

    add_lost_pv_to_all_cells(dic)
    add_lost_pv_to_all_eq_cells(dic)
    add_lost_pv_to_all_fip_cells(dic)
    identify_removed_pilars(dic)


def add_lost_pv_to_boundary_cells(dic, inx, num):
    """
    Function to correct the lost pore volume on the cell boundaries

    Args:
        dic (dict): Global dictionary with required parameters\n
        inx (array): Index of the reference cells in the coarser block\n
        num (int): Global index of the reference cell

    Returns:
        dic (dict): Modified global dictionary

    """
    for i in range(dic["nz"]):
        if dic["actnum_c"][num - (i + 1)] > 0:
            indic = num - (i + 1)
            dic["BI"] = dic["con"] == indic + 1
            for k in range(len(dic["index"][indic])):
                dic["BI"] = np.logical_or(
                    dic["BI"],
                    dic["con"] == (int(dic["index"][indic][k]) + 1),
                )
            inxb = np.where(dic["BI"])
            dic["index"][indic].append(indic)
            dic["porv_c"][indic] = sum(
                dic["poro"][inx] * dic["vol"][inx] * dic["actnum"][inx]
            ) + sum(dic["poro"][inxb] * dic["vol"][inxb] * dic["actnum"][inxb])
            if dic["ntg_c"][indic] > 1.0:
                dic["ntg_c"][indic] = 1.0
                dic["poro_c"][indic] = min(
                    1.0,
                    (
                        sum(
                            dic["poro"][inx]
                            * dic["vol"][inx]
                            * dic["ntg"][inx]
                            * dic["actnum"][inx]
                        )
                        + sum(
                            dic["poro"][inxb]
                            * dic["vol"][inxb]
                            * dic["ntg"][inxb]
                            * dic["actnum"][inxb]
                        )
                    )
                    / (dic["vol_c"][indic] * dic["actnum_c"][indic]),
                )
            break
        if dic["actnum_c"][num - (i + 1) * dic["nx"]] > 0:
            indic = num - (i + 1) * dic["nx"]
            dic["BI"] = dic["con"] == indic + 1
            for k in range(len(dic["index"][indic])):
                dic["BI"] = np.logical_or(
                    dic["BI"], dic["con"] == (int(dic["index"][indic][k]) + 1)
                )
            inxb = np.where(dic["BI"])
            dic["index"][indic].append(indic)
            dic["porv_c"][indic] = sum(
                dic["poro"][inx] * dic["vol"][inx] * dic["actnum"][inx]
            ) + sum(dic["poro"][inxb] * dic["vol"][inxb] * dic["actnum"][inxb])
            if dic["ntg_c"][indic] > 1.0:
                dic["ntg_c"][indic] = 1.0
                dic["poro_c"][indic] = min(
                    1.0,
                    (
                        sum(
                            dic["poro"][inx]
                            * dic["vol"][inx]
                            * dic["ntg"][inx]
                            * dic["actnum"][inx]
                        )
                        + sum(
                            dic["poro"][inxb]
                            * dic["vol"][inxb]
                            * dic["ntg"][inxb]
                            * dic["actnum"][inxb]
                        )
                    )
                    / (dic["vol_c"][indic] * dic["actnum_c"][indic]),
                )
            break
        if dic["actnum_c"][num - (i + 1) * dic["nx"] * dic["ny"]] > 0:
            indic = num - (i + 1) * dic["nx"] * dic["ny"]
            dic["BI"] = dic["con"] == indic + 1
            for k in range(len(dic["index"][indic])):
                dic["BI"] = np.logical_or(
                    dic["BI"], dic["con"] == (int(dic["index"][indic][k]) + 1)
                )
            inxb = np.where(dic["BI"])
            dic["index"][indic].append(indic)
            dic["porv_c"][indic] = sum(
                dic["poro"][inx] * dic["vol"][inx] * dic["actnum"][inx]
            ) + sum(dic["poro"][inxb] * dic["vol"][inxb] * dic["actnum"][inxb])
            if dic["ntg_c"][indic] > 1.0:
                dic["ntg_c"][indic] = 1.0
                dic["poro_c"][indic] = min(
                    1.0,
                    (
                        sum(
                            dic["poro"][inx]
                            * dic["vol"][inx]
                            * dic["ntg"][inx]
                            * dic["actnum"][inx]
                        )
                        + sum(
                            dic["poro"][inxb]
                            * dic["vol"][inxb]
                            * dic["ntg"][inxb]
                            * dic["actnum"][inxb]
                        )
                    )
                    / (dic["vol_c"][indic] * dic["actnum_c"][indic]),
                )
            break


def add_lost_pv_to_all_cells(dic):
    """
    Method to correct the lost pore volume on all active cells

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    if dic["cporv"] != 2:
        return
    pv_c = sum(
        np.array(dic["poro_c"])
        * np.array(dic["vol_c"])
        * np.array(dic["ntg_c"])
        * np.array(dic["actnum_c"])
    )
    corr = sum(dic["poro"] * dic["vol"] * dic["ntg"] * dic["actnum"]) / pv_c
    for i in range(dic["num_cells"]):
        dic["porv_c"][i] *= corr


def add_lost_pv_to_all_eq_cells(dic):
    """
    Method to correct the lost pore volume by distributing it to the
    same eqlnum

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    if dic["cporv"] != 3:
        return

    for i in range(1, 8):
        pv_c = sum(
            np.array(dic["poro_c"])
            * np.array(dic["vol_c"])
            * np.array(dic["ntg_c"])
            * np.array(dic["actnum_c"])
            * np.equal(np.array(dic["eqlnum_c"]), i)
        )
        corr = (
            sum(
                dic["poro"]
                * dic["vol"]
                * dic["ntg"]
                * dic["actnum"]
                * np.equal(np.array(dic["eqlnum"]), i)
            )
            / pv_c
        )
        for j in range(dic["num_cells"]):
            if dic["eqlnum_c"][j] == i:
                dic["porv_c"][j] *= corr


def add_lost_pv_to_all_fip_cells(dic):
    """
    Method to correct the lost pore volume by distributing it to the
    same fipnum

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    if dic["cporv"] != 4:
        return

    for i in range(1, 22):
        pv_c = sum(
            np.array(dic["poro_c"])
            * np.array(dic["vol_c"])
            * np.array(dic["ntg_c"])
            * np.array(dic["actnum_c"])
            * np.equal(np.array(dic["fipnum_c"]), i)
        )
        corr = (
            sum(
                dic["poro"]
                * dic["vol"]
                * dic["ntg"]
                * dic["actnum"]
                * np.equal(np.array(dic["fipnum"]), i)
            )
            / pv_c
        )
        for j in range(dic["num_cells"]):
            if dic["fipnum_c"][j] == i:
                dic["porv_c"][j] *= corr


def identify_removed_pilars(dic):
    """
    Identify the removed pilars to be used to write the coarser grid

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["mr"] = []
    dic["ir"] = []
    for i in range(dic["nd"][0] + 1):
        if (dic["X"][i]) > 1:
            for k in range(
                i, (dic["nd"][0] + 1) * (dic["nd"][1] + 1), dic["nd"][0] + 1
            ):
                for j in range(6):
                    dic["mr"].append(k * 6 + j)
            for num in range(
                2 * i - 1,
                8 * dic["nc"],
                2 * dic["nd"][0],
            ):
                dic["ir"].append(num)
                dic["ir"].append(num + 1)

    for j in range(dic["nd"][1] + 1):
        if (dic["Y"][j]) > 1:
            for k in range(j * (dic["nd"][0] + 1), (j + 1) * (dic["nd"][0] + 1)):
                for i in range(6):
                    dic["mr"].append(k * 6 + i)
            for num in range(
                (2 * j - 1) * 2 * dic["nd"][0],
                8 * dic["nc"],
                4 * dic["nd"][0] * dic["nd"][1],
            ):
                for i in range(4 * dic["nd"][0]):
                    dic["ir"].append(num + i)
    identify_removed_pilars_zdir(dic)


def identify_removed_pilars_zdir(dic):
    """
    Identify the removed pilars in the z direction

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    for k in range(dic["nd"][2] + 1):
        if (dic["Z"][k]) > 1:
            for num in range(
                (2 * k - 1) * 4 * dic["nd"][0] * dic["nd"][1],
                (2 * k + 1) * 4 * dic["nd"][0] * dic["nd"][1],
            ):
                dic["ir"].append(num)
