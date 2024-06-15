# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""
Utiliy functions for the generation of the grids.
"""


def coarser_grid(dic):
    """Function to coarse the grid"""
    num, num_c = 0, 1
    for k in range(dic["grid"].nz):
        for j in range(dic["grid"].ny):
            for i in range(dic["grid"].nx):
                if dic["con"][num] == 0:
                    dic["con"][num] = num_c
                    num_c += 1
                if (dic["X"][i + 1]) > 1:
                    dic["con"][num + 1] = dic["con"][num]
                if (dic["Y"][j + 1]) > 1:
                    dic["con"][num + dic["grid"].nx] = dic["con"][num]
                if (dic["Z"][k + 1]) > 1:
                    dic["con"][num + dic["grid"].nx * dic["grid"].ny] = dic["con"][num]
                num += 1

    dic["nx"] = dic["grid"].nx - int(sum(dic["X"] == 2))
    dic["ny"] = dic["grid"].ny - int(sum(dic["Y"] == 2))
    dic["nz"] = dic["grid"].nz - int(sum(dic["Z"] == 2))

    dic["num_cells"] = dic["nx"] * dic["ny"] * dic["nz"]

    name = ["i_f_c", "j_f_c", "k_f_c"]
    axis = ["X", "Y", "Z"]
    grid = [dic["grid"].nx, dic["grid"].ny, dic["grid"].nz]
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
    dic = handle_faults(dic)
    return dic


def handle_face_dir_ip(dic, cell_index, i, j, k):
    """Method for the face I+ dir"""
    i1 = i
    i2 = i + 1
    while dic["i_f_c"][i1 + 1] == dic["i_f_c"][i2 + 1]:
        index1 = [
            cell_index,
            cell_index + 2 * dic["grid"].nx,
            cell_index + 4 * dic["grid"].nx * dic["grid"].ny,
            cell_index + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        index2 = [
            index1[0] + 3,
            index1[1] + 3,
            index1[0] + 3 + 4 * dic["grid"].nx * dic["grid"].ny,
            index1[1] + 3 + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        if j + 1 < dic["grid"].ny and (dic["j_f_c"][j + 1] == dic["j_f_c"][j + 2]):
            cell_index2 = (
                2 * i
                + 4 * (j + 1) * dic["grid"].nx
                + 8 * k * dic["grid"].nx * dic["grid"].ny
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["grid"].nx,
                cell_index2 + 4 * dic["grid"].nx * dic["grid"].ny,
                cell_index2 + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]

        if j > 0 and (dic["j_f_c"][j + 1] == dic["j_f_c"][j]):
            cell_index2 = (
                2 * i
                + 4 * (j - 1) * dic["grid"].nx
                + 8 * k * dic["grid"].nx * dic["grid"].ny
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["grid"].nx,
                cell_index2 + 4 * dic["grid"].nx * dic["grid"].ny,
                cell_index2 + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]
        i2 = i2 + 1


def handle_face_dir_im(dic, cell_index, i, j, k):
    """Method for the face I- dir"""
    i1 = i
    i2 = i - 1
    while dic["i_f_c"][i1 + 1] == dic["i_f_c"][i2 + 1]:
        index1 = [
            cell_index + 1,
            cell_index + 1 + 2 * dic["grid"].nx,
            cell_index + 1 + 4 * dic["grid"].nx * dic["grid"].ny,
            cell_index + 1 + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        index2 = [
            index1[0] - 3,
            index1[1] - 3,
            index1[0] - 3 + 4 * dic["grid"].nx * dic["grid"].ny,
            index1[1] - 3 + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        if j + 1 < dic["grid"].ny and (dic["j_f_c"][j + 1] == dic["j_f_c"][j + 2]):
            cell_index2 = (
                2 * i
                + 4 * (j + 1) * dic["grid"].nx
                + 8 * k * dic["grid"].nx * dic["grid"].ny
                + 1
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["grid"].nx,
                cell_index2 + 4 * dic["grid"].nx * dic["grid"].ny,
                cell_index2 + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]

        if j > 0 and (dic["j_f_c"][j + 1] == dic["j_f_c"][j]):
            cell_index2 = (
                2 * i
                + 4 * (j - 1) * dic["grid"].nx
                + 8 * k * dic["grid"].nx * dic["grid"].ny
                + 1
            )
            index1 = [
                cell_index2,
                cell_index2 + 2 * dic["grid"].nx,
                cell_index2 + 4 * dic["grid"].nx * dic["grid"].ny,
                cell_index2 + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
            ]
            for iter1, iter2 in zip(index1, index2):
                dic["zc"][iter1] = dic["zc"][iter2]
        i2 = i2 - 1


def handle_face_dir_jp(dic, cell_index, j):
    """Method for the face J+ dir"""
    j1 = j
    j2 = j + 1
    while dic["j_f_c"][j1 + 1] == dic["j_f_c"][j2 + 1]:
        index1 = [
            cell_index,
            cell_index + 1,
            cell_index + 4 * dic["grid"].nx * dic["grid"].ny,
            cell_index + 1 + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        index2 = [
            index1[0] + 6 * dic["grid"].nx,
            index1[1] + 6 * dic["grid"].nx,
            index1[0] + 6 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
            index1[1] + 6 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        j2 = j2 + 1


def handle_face_dir_jm(dic, cell_index, j):
    """Method for the face J- dir"""
    j1 = j
    j2 = j - 1
    while dic["j_f_c"][j1 + 1] == dic["j_f_c"][j2 + 1]:
        index1 = [
            cell_index + 2 * dic["grid"].nx,
            cell_index + 1 + 2 * dic["grid"].nx,
            cell_index + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
            cell_index + 1 + 2 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        index2 = [
            index1[0] - 6 * dic["grid"].nx,
            index1[1] - 6 * dic["grid"].nx,
            index1[0] - 6 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
            index1[1] - 6 * dic["grid"].nx + 4 * dic["grid"].nx * dic["grid"].ny,
        ]
        for iter1, iter2 in zip(index1, index2):
            dic["zc"][iter1] = dic["zc"][iter2]

        j2 = j2 - 1


def handle_faults(dic):
    """Method for the fault approach"""
    for f in dic["fault"]:
        if len(f) == 0:
            continue
        for i in range(int(f[0]) - 1, int(f[1])):
            for j in range(int(f[2]) - 1, int(f[3])):
                for k in range(int(f[4]) - 1, int(f[5])):
                    cell_index = (
                        2 * i
                        + 4 * j * dic["grid"].nx
                        + 8 * k * dic["grid"].nx * dic["grid"].ny
                    )
                    if f[6] == "I":
                        handle_face_dir_ip(dic, cell_index, i, j, k)
                    if f[6] == "I-":
                        handle_face_dir_im(dic, cell_index, i, j, k)
                    if f[6] == "J":
                        handle_face_dir_jp(dic, cell_index, j)
                    if f[6] == "J-":
                        handle_face_dir_jm(dic, cell_index, j)
    return dic
