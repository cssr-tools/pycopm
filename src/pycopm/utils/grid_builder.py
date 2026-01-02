# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""
Utiliy functions for coarsened corner-point grids from toml configuration files.
"""

import numpy as np


def coarser_grid(dic):
    """
    Method to coarse the grid

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    num, num_c = 0, 1
    for k in range(dic["nd"][2]):
        for j in range(dic["nd"][1]):
            for i in range(dic["nd"][0]):
                if dic["con"][num] == 0:
                    dic["con"][num] = num_c
                    num_c += 1
                if (dic["X"][i + 1]) > 1:
                    dic["con"][num + 1] = dic["con"][num]
                if (dic["Y"][j + 1]) > 1:
                    dic["con"][num + dic["nd"][0]] = dic["con"][num]
                if (dic["Z"][k + 1]) > 1:
                    dic["con"][num + dic["nd"][0] * dic["nd"][1]] = dic["con"][num]
                num += 1
    dic["nx"] = dic["nd"][0] - int(np.sum(dic["X"] == 2))
    dic["ny"] = dic["nd"][1] - int(np.sum(dic["Y"] == 2))
    dic["nz"] = dic["nd"][2] - int(np.sum(dic["Z"] == 2))

    dic["num_cells"] = dic["nx"] * dic["ny"] * dic["nz"]

    name = ["i_f_c", "j_f_c", "k_f_c"]
    axis = ["X", "Y", "Z"]
    grid = [dic["nd"][0], dic["nd"][1], dic["nd"][2]]
    for name, axis, grid in zip(name, axis, grid):
        num = 1
        num_c = 1
        for i in range(grid):
            if dic[name][num] == 0:
                dic[name][num] = num_c
                num_c += 1
            if (dic[axis][i + 1]) > 1:
                dic[name][num + 1] = dic[name][num]
            num += 1
    handle_faults(dic)


def handle_face_dir_ip(dic, cell_index, i, j, k):
    """
    Method for the face I+ dir

    Args:
        dic (dict): Global dictionary\n
        cell_index (int): Global index of the cell position\n
        i (int): i index of the cell position\n
        j (int): j index of the cell position\n
        k (int): k index of the cell position

    Returns:
        dic (dict): Modified global dictionary

    """
    i1 = i
    i2 = i + 1
    while dic["i_f_c"][i1 + 1] == dic["i_f_c"][i2 + 1]:
        index1 = [
            cell_index,
            cell_index + 2 * dic["nd"][0],
            cell_index + 4 * dic["nd"][0] * dic["nd"][1],
            cell_index + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        index2 = [
            index1[0] + 3,
            index1[1] + 3,
            index1[0] + 3 + 4 * dic["nd"][0] * dic["nd"][1],
            index1[1] + 3 + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        if j + 1 < dic["nd"][1] and (dic["j_f_c"][j + 1] == dic["j_f_c"][j + 2]):
            cell_index2 = (
                2 * i + 4 * (j + 1) * dic["nd"][0] + 8 * k * dic["nd"][0] * dic["nd"][1]
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["nd"][0],
                cell_index2 + 4 * dic["nd"][0] * dic["nd"][1],
                cell_index2 + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]

        if j > 0 and (dic["j_f_c"][j + 1] == dic["j_f_c"][j]):
            cell_index2 = (
                2 * i + 4 * (j - 1) * dic["nd"][0] + 8 * k * dic["nd"][0] * dic["nd"][1]
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["nd"][0],
                cell_index2 + 4 * dic["nd"][0] * dic["nd"][1],
                cell_index2 + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]
        i2 = i2 + 1


def handle_face_dir_im(dic, cell_index, i, j, k):
    """
    Method for the face I- dir

    Args:
        dic (dict): Global dictionary\n
        cell_index (int): Global index of the cell position\n
        i (int): i index of the cell position\n
        j (int): j index of the cell position\n
        k (int): k index of the cell position

    Returns:
        dic (dict): Modified global dictionary

    """
    i1 = i
    i2 = i - 1
    while dic["i_f_c"][i1 + 1] == dic["i_f_c"][i2 + 1]:
        index1 = [
            cell_index + 1,
            cell_index + 1 + 2 * dic["nd"][0],
            cell_index + 1 + 4 * dic["nd"][0] * dic["nd"][1],
            cell_index + 1 + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        index2 = [
            index1[0] - 3,
            index1[1] - 3,
            index1[0] - 3 + 4 * dic["nd"][0] * dic["nd"][1],
            index1[1] - 3 + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        if j + 1 < dic["nd"][1] and (dic["j_f_c"][j + 1] == dic["j_f_c"][j + 2]):
            cell_index2 = (
                2 * i
                + 4 * (j + 1) * dic["nd"][0]
                + 8 * k * dic["nd"][0] * dic["nd"][1]
                + 1
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["nd"][0],
                cell_index2 + 4 * dic["nd"][0] * dic["nd"][1],
                cell_index2 + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]

        if j > 0 and (dic["j_f_c"][j + 1] == dic["j_f_c"][j]):
            cell_index2 = (
                2 * i
                + 4 * (j - 1) * dic["nd"][0]
                + 8 * k * dic["nd"][0] * dic["nd"][1]
                + 1
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["nd"][0],
                cell_index2 + 4 * dic["nd"][0] * dic["nd"][1],
                cell_index2 + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]
        i2 = i2 - 1


def handle_face_dir_jp(dic, cell_index, j):
    """
    Method for the face J+ dir

    Args:
        dic (dict): Global dictionary\n
        cell_index (int): Global index of the cell position\n
        j (int): j index of the cell position

    Returns:
        dic (dict): Modified global dictionary

    """
    j1 = j
    j2 = j + 1
    while dic["j_f_c"][j1 + 1] == dic["j_f_c"][j2 + 1]:
        index1 = [
            cell_index,
            cell_index + 1,
            cell_index + 4 * dic["nd"][0] * dic["nd"][1],
            cell_index + 1 + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        index2 = [
            index1[0] + 6 * dic["nd"][0],
            index1[1] + 6 * dic["nd"][0],
            index1[0] + 6 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
            index1[1] + 6 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        j2 = j2 + 1


def handle_face_dir_jm(dic, cell_index, j):
    """
    Method for the face J- dir

    Args:
        dic (dict): Global dictionary\n
        cell_index (int): Global index of the cell position\n
        j (int): j index of the cell position

    Returns:
        dic (dict): Modified global dictionary

    """
    j1 = j
    j2 = j - 1
    while dic["j_f_c"][j1 + 1] == dic["j_f_c"][j2 + 1]:
        index1 = [
            cell_index + 2 * dic["nd"][0],
            cell_index + 1 + 2 * dic["nd"][0],
            cell_index + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
            cell_index + 1 + 2 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        index2 = [
            index1[0] - 6 * dic["nd"][0],
            index1[1] - 6 * dic["nd"][0],
            index1[0] - 6 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
            index1[1] - 6 * dic["nd"][0] + 4 * dic["nd"][0] * dic["nd"][1],
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        j2 = j2 - 1


def handle_faults(dic):
    """
    Method for the fault i,j,k mapping from reference to coarse positions

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    for f in dic["fault"]:
        if len(f) == 0:
            continue
        for i in range(int(f[0]) - 1, int(f[1])):
            for j in range(int(f[2]) - 1, int(f[3])):
                for k in range(int(f[4]) - 1, int(f[5])):
                    cell_index = (
                        2 * i
                        + 4 * j * dic["nd"][0]
                        + 8 * k * dic["nd"][0] * dic["nd"][1]
                    )
                    if f[6] == "I":
                        handle_face_dir_ip(dic, cell_index, i, j, k)
                    if f[6] == "I-":
                        handle_face_dir_im(dic, cell_index, i, j, k)
                    if f[6] == "J":
                        handle_face_dir_jp(dic, cell_index, j)
                    if f[6] == "J-":
                        handle_face_dir_jm(dic, cell_index, j)
