# SPDX-FileCopyrightText: 2024-2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911,R1705

"""
Methods to parser the input OPM deck.
"""

import sys
import csv
import numpy as np

csv.field_size_limit(sys.maxsize)


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
    dic["welsegs"] = False
    dic["complump"] = False
    dic["compdat"] = False
    dic["compsegs"] = False
    dic["mapaxes"] = False
    dic["multregt"] = False
    dic["edit"] = False
    dic["editnnc"] = False
    dic["multiply"] = False
    dic["prop"] = False
    dic["oper"] = False
    dic["region"] = False
    dic["equil"] = False
    dic["schedule"] = False
    dic["fault"] = False
    dic["rptsrt"] = False
    dic["multflt"] = False
    dic["dimens"] = False
    dic["welldims"] = False
    dic["wells"] = False
    dic["skip"] = False
    dic["aqucon"] = False
    dic["aqunum"] = False
    dic["aquancon"] = False
    dic["bccon"] = False
    dic["bwpr"] = False
    dic["source"] = False
    dic["pinch"] = False
    dic["kedit"] = False
    dic["edit0"] = ""
    dic["nsegw"] = []
    dic["nwells"] = []
    dic["awells"] = []
    dic["swells"] = []
    dic["lines"] = []
    if dic["refinement"]:
        names_segwells(dic)
    elif dic["vicinity"]:
        names_wells(dic)
    with open(dic["deck"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            nrwo = nrwo.replace("\\t", " ")
            nrwo = nrwo.replace("', '", ",")
            nrwo = nrwo.replace("-- Generated : Petrel", "")
            nrwo = nrwo.strip()
            if not dic["lines"] and np.sum("-" == line for line in nrwo) > 70:
                dic["lines"] = nrwo
            if not dic["schedule"]:
                dic["lolc"].append(nrwo)
            if handle_dimens(dic, nrwo):
                continue
            if handle_welldims(dic, nrwo):
                continue
            if handle_grid_props(dic, nrwo):
                continue
            if handle_props(dic, nrwo):
                continue
            if handle_regions(dic, nrwo):
                continue
            if handle_equil(dic, nrwo):
                continue
            if handle_bwpr(dic, nrwo):
                continue
            if handle_schedule(dic, nrwo):
                continue
            if handle_wells(dic, nrwo):
                continue
            if handle_source(dic, nrwo):
                continue
            if handle_aquancon(dic, nrwo):
                continue
            if dic["vicinity"]:
                if handle_welsegs(dic, nrwo):
                    continue
                # if handle_compsegs(dic, nrwo):
                #     continue
                if handle_schedulekw(dic, nrwo):
                    continue
            if handle_segmented_wells(dic, nrwo):
                continue
            if len(dic["lol"]) > 0:
                for case in dic["special"]:
                    if case + "." in nrwo.lower() or "." + case in nrwo.lower():
                        nrwo = f"{dic['label']}{case.upper()}.INC /"
                    elif dic["lol"][-1] == "INCLUDE" and case in nrwo.lower():
                        nrwo = f"{dic['label']}{case.upper()}.INC /"
            dic["lol"].append(nrwo)


def handle_schedulekw(dic, nrwo):
    """
    Handle special keywords in the schedule for wells in submodels

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    for name in dic["kw"]:
        if nrwo == name.upper():
            dic[name] = True
            dic["lol"].append(nrwo)
            return True
        if dic[name]:
            edit = nrwo.split()
            if edit:
                if edit[0] == "/":
                    dic[name] = False
            if len(edit) > 1:
                if edit[0][:2] != "--":
                    well = edit[0].replace("'", "")
                    if name == "wsegvalv":
                        if well in dic["swells"]:
                            return True
                    if well[-1] == "*":
                        n = len(well[:-1])
                        for well1 in dic["nwells"]:
                            if well1[:n] == well[:-1]:
                                return False
                    if well not in dic["nwells"]:
                        return True
                else:
                    return True
    return False


def get_wells_for_vicinity(dic):
    """
    Get the names and i,j,k indices for the wells

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    compdat = False
    with open(dic["deck"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            if nrwo == "COMPDAT":
                compdat = True
                continue
            if compdat:
                edit = nrwo.split()
                if edit:
                    if edit[0] == "/":
                        dic["edit0"] = ""
                        compdat = False
                    well = edit[0].replace("'", "")
                    if well != dic["optvic"]:
                        continue
                    if len(edit) > 2:
                        if edit[0][:2] != "--":
                            for i in range(int(edit[3]), int(edit[4]) + 1):
                                dic["wvicinity"].append(
                                    [int(edit[1]) - 1, int(edit[2]) - 1, i - 1]
                                )


def names_wells(dic):
    """
    Get the names of the wells in the submodel

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    swell = ""
    with open(dic["deck"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            if nrwo == "COMPDAT":
                dic["compdat"] = True
                continue
            if dic["compdat"]:
                edit = nrwo.split()
                if edit:
                    if edit[0] == "/":
                        dic["edit0"] = ""
                        dic["compdat"] = False
                    well = edit[0].replace("'", "")
                    if well in dic["nwells"]:
                        continue
                if len(edit) > 2:
                    if edit[0][:2] != "--":
                        if well not in dic["awells"]:
                            dic["awells"].append(well)
                        if (
                            dic["ic"][int(edit[1])]
                            * dic["jc"][int(edit[2])]
                            * dic["kc"][int(edit[3])]
                            * dic["kc"][int(edit[4])]
                            > 0
                        ):
                            dic["nwells"].append(well)
            if nrwo == "COMPSEGS":
                dic["compsegs"] = True
                continue
            if dic["compsegs"]:
                edit = nrwo.split()
                if edit:
                    if edit[0] == "/":
                        dic["compsegs"] = False
                if len(edit) > 1:
                    if edit[0][:2] != "--":
                        well = edit[0].replace("'", "")
                        if well in dic["awells"]:
                            swell = well
                        elif (
                            dic["ic"][int(edit[0])]
                            * dic["jc"][int(edit[1])]
                            * dic["kc"][int(edit[2])]
                            != 0
                        ):
                            if swell not in dic["swells"]:
                                dic["swells"].append(swell)
    dic["kw"] = [
        "wconhist",
        "wdfac",
        "weltarg",
        "wrftplt",
        "weltarg",
        "compord",
        "wtracer",
        "wconinjh",
        "wconinje",
        "wconprod",
        "wtest",
        "welopen",
        "wsegvalv",
        "wecon",
        "cskin",
        "wpavedep",
    ]
    for name in dic["kw"]:
        dic[name] = False
    if dic["wvicinity"]:
        for n in ["s", "n", "a"]:
            dic[f"{n}wells"] = [
                val.replace("'", "")
                for val in dic[f"{n}wells"]
                if val in [dic["optvic"], f"'{dic['optvic']}'"]
            ]


def names_segwells(dic):
    """
    Get the names of segmented wells

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    with open(dic["deck"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            if nrwo == "COMPDAT":
                dic["compdat"] = True
                continue
            if dic["compdat"]:
                edit = nrwo.split()
                if edit:
                    if edit[0] == "/":
                        dic["compdat"] = False
                    well = edit[0].replace("'", "")
                    if well in dic["swells"]:
                        continue
                    if len(edit) > 2:
                        if edit[0][:2] != "--":
                            if dic["edit0"] == "":
                                dic["edit0"] = nrwo.split()
                            else:
                                well0 = dic["edit0"][0].replace("'", "")
                                if (
                                    edit[1] != dic["edit0"][1]
                                    or edit[2] != dic["edit0"][2]
                                ) and well == well0:
                                    dic["swells"].append(str(well))
                            dic["edit0"] = nrwo.split()
            if nrwo == "COMPSEGS":
                dic["compsegs"] = True
                continue
            if dic["compsegs"]:
                edit = nrwo.split()
                if len(edit) > 1:
                    well = edit[0].replace("'", "")
                    if edit[0][:2] != "--":
                        dic["nsegw"].append(str(well))
                        dic["compsegs"] = False


def handle_dimens(dic, nrwo):
    """
    Handle the grid dimensions

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "DIMENS":
        dic["dimens"] = True
        dic["lol"].append(nrwo)
        dic["lol"].append(f"{dic['nx']} {dic['ny']} {dic['nz']} /")
        return True
    if dic["dimens"]:
        edit = nrwo.split()
        if edit:
            if edit[0][:2] != "--":
                if edit[-1] == "/" or edit[0] == "/":
                    dic["dimens"] = False
        return True
    return False


def handle_welldims(dic, nrwo):
    """
    Handle the  well dimensions

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if not dic["refinement"]:
        return False
    if nrwo == "WELLDIMS":
        dic["welldims"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["welldims"]:
        edit = nrwo.split()
        if edit:
            if edit[0][:2] != "--":
                if len(edit) > 2:
                    edit[1] = str(dic["nx"] + (dic["ny"]) + (dic["nz"]))
                    dic["lol"].append(" ".join(edit))
                    if "/" in nrwo:
                        dic["welldims"] = False
                if edit[0] == "/":
                    dic["lol"].append(nrwo)
                    dic["welldims"] = False
        return True
    return False


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
        if dic["lines"]:
            dic["lol"].append(dic["lines"])
        dic["lol"].append(nrwo)
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
                if dic["refinement"]:
                    edit[2] = str(dic["i1"][int(edit[2])])
                    edit[3] = str(dic["in"][int(edit[3])])
                    edit[4] = str(dic["j1"][int(edit[4])])
                    edit[5] = str(dic["jn"][int(edit[5])])
                    edit[6] = str(dic["k1"][int(edit[6])])
                    edit[7] = str(dic["kn"][int(edit[7])])
                elif dic["vicinity"]:
                    if (
                        (
                            (dic["mini"] - int(edit[2]) + 1) > 0
                            or (int(edit[3]) - dic["maxi"] + 1) > 0
                            or dic["ic"][int(edit[3])] > 0
                        )
                        and (
                            (dic["minj"] - int(edit[4]) + 1) > 0
                            or (int(edit[5]) - dic["maxj"] + 1) > 0
                            or dic["jc"][int(edit[5])] > 0
                        )
                        and (
                            (dic["mink"] - int(edit[6]) + 1) > 0
                            or (int(edit[7]) - dic["maxk"] + 1) > 0
                            or dic["kc"][int(edit[7])] > 0
                        )
                    ):
                        edit[2] = str(max(1, dic["ic"][int(edit[2])]))
                        edit[3] = str(
                            dic["nx"]
                            if dic["ic"][int(edit[3])] == 0
                            else dic["ic"][int(edit[3])]
                        )
                        edit[4] = str(max(1, dic["jc"][int(edit[4])]))
                        edit[5] = str(
                            dic["ny"]
                            if dic["jc"][int(edit[5])] == 0
                            else dic["jc"][int(edit[5])]
                        )
                        edit[6] = str(max(1, dic["kc"][int(edit[6])]))
                        edit[7] = str(
                            dic["nz"]
                            if dic["kc"][int(edit[7])] == 0
                            else dic["kc"][int(edit[7])]
                        )
                    else:
                        return True
                else:
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
        dic["lol"].append(nrwo)
        if dic["fipcorr"] == 1:
            dic["deckcorr"] = dic["lol"].copy()
            if dic["nrptsrt"] > 0:
                dic["deckcorr"][dic["nrptsrt"]] = dic["fip"]
                dic["lolc"][dic["nrptsrtc"]] = dic["fip"]
            else:
                dic["deckcorr"].append("RPTRST")
                dic["deckcorr"].append("FIP /")
                dic["lolc"].append("RPTRST")
                dic["lolc"].append("FIP /")
            dic["deckcorr"].append("TSTEP")
            dic["deckcorr"].append("0.01 /")
            dic["lolc"].append("TSTEP")
            dic["lolc"].append("0.01 /")
        return True
    return False


def handle_bwpr(dic, nrwo):
    """
    Handle the block pressure

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "BWPR":
        dic["bwpr"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["bwpr"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["bwpr"] = False
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["vicinity"]:
                    if (
                        dic["ic"][int(edit[0])]
                        * dic["jc"][int(edit[1])]
                        * dic["jc"][int(edit[2])]
                        == 0
                    ):
                        return True
                edit[0] = str(dic["ic"][int(edit[0])])
                edit[1] = str(dic["jc"][int(edit[1])])
                edit[2] = str(dic["kc"][int(edit[2])])
                dic["lol"].append(" ".join(edit))
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
        dic["lol"].append(nrwo)
        if dic["lol"][-2][:3] == "---":
            dic["lol"].append(dic["lol"][-2])
        return True
    if dic["region"]:
        if nrwo == "SOLUTION":
            dic["region"] = False
            for name in dic["regions"]:
                dic["lol"].append("INCLUDE")
                dic["lol"].append(f"'{dic['label']}{name.upper()}.INC' /\n")
            if dic["lines"]:
                dic["lol"].append(dic["lines"])
        else:
            return True
    return False


def handle_equil(dic, nrwo):
    """
    Handle the solution sections

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if not dic["explicit"]:
        return False
    if "EQUIL" in nrwo:
        edit = nrwo.split()
        if edit[0] != "EQUIL":
            return False
        dic["equil"] = True
        dic["lol"].append("--EQUIL --pycopm explicit initialization")
        return True
    if dic["equil"]:
        edit = nrwo.split()
        if edit:
            if edit[0][:2] != "--":
                if not edit[0][0].isdigit():
                    write_explicit(dic)
                    dic["lol"].append(edit[0])
                    dic["equil"] = False
                else:
                    dic["lol"].append("--" + nrwo)
            else:
                dic["lol"].append("--" + nrwo)
        return True
    return False


def write_explicit(dic):
    """
    Write the explicit solution

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    for name in dic["rptrst"]:
        dic["lol"].append("INCLUDE")
        dic["lol"].append(f"'{dic['label']}{name.upper()}.INC' /\n")


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
        dic["lol"].append(nrwo)
        if dic["lol"][-2][:3] == "---":
            dic["lol"].append(dic["lol"][-2])
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
        if handle_aqunum(dic, nrwo):
            return True
        if handle_aqucon(dic, nrwo):
            return True
        if handle_aquancon(dic, nrwo):
            return True
        if handle_bccon(dic, nrwo):
            return True
        # if handle_oper(dic, nrwo):
        #    return True
        if nrwo == "EDIT":
            dic["kedit"] = True
            if dic["lines"]:
                dic["lol"].append(dic["lines"])
            dic["lol"].append(nrwo)
            if dic["lines"]:
                dic["lol"].append(dic["lines"])
        if dic["trans"] == 0:
            if handle_pinch(dic, nrwo):
                return True
            if handle_multregt(dic, nrwo):
                return True
            if handle_multflt(dic, nrwo):
                return True
            if nrwo == "EDIT":
                dic["edit"] = True
                dic["lol"].append("INCLUDE")
                dic["lol"].append(f"'{dic['label']}PORV.INC' /\n")
        if nrwo == "PROPS":
            dic["removeg"] = False
            if not dic["edit"]:
                if not dic["kedit"]:
                    if dic["lines"]:
                        dic["lol"].append(dic["lines"])
                    dic["lol"].append("EDIT")
                    if dic["lines"]:
                        dic["lol"].append(dic["lines"])
                dic["lol"].append("INCLUDE")
                dic["lol"].append(f"'{dic['label']}PORV.INC' /\n")
                if dic["trans"] > 0:
                    for name in ["tranx", "trany", "tranz"]:
                        dic["lol"].append("INCLUDE")
                        dic["lol"].append(f"'{dic['label']}{name.upper()}.INC' /\n")
        elif dic["edit"] or (dic["kedit"] and (dic["refinement"] or dic["vicinity"])):
            if handle_editnnc(dic, nrwo):
                return True
            if handle_multiply(dic, nrwo):
                return True
        else:
            return True
    return False


def handle_aqunum(dic, nrwo):
    """
    Handle the i,j,k aquifer numbers

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "AQUNUM":
        dic["aqunum"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["aqunum"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["lol"].append(nrwo)
                dic["aqunum"] = False
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["vicinity"]:
                    if (
                        dic["ic"][int(edit[1])]
                        * dic["jc"][int(edit[2])]
                        * dic["jc"][int(edit[3])]
                        == 0
                    ):
                        return True
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["jc"][int(edit[2])])
                edit[3] = str(dic["kc"][int(edit[3])])
                dic["lol"].append(" ".join(edit))
                return True
    return False


def handle_aquancon(dic, nrwo):
    """
    Handle the modified i,j,k aquancon indices

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "AQUANCON":
        dic["aquancon"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["aquancon"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["lol"].append(nrwo)
                dic["aquancon"] = False
                return True
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["refinement"]:
                    dcn = edit[7]
                    edit0 = edit.copy()
                    if dcn in ["I", "X"]:
                        edit0[1] = str(dic["in"][int(edit[1])])
                        edit0[2] = str(dic["in"][int(edit[2])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["j1"][int(edit[3])], dic["jn"][int(edit[4])] + 1
                        ):
                            edit0[3] = str(i)
                            edit0[4] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["I-", "X-"]:
                        edit0[1] = str(dic["i1"][int(edit[1])])
                        edit0[2] = str(dic["i1"][int(edit[2])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["j1"][int(edit[3])], dic["jn"][int(edit[4])] + 1
                        ):
                            edit0[3] = str(i)
                            edit0[4] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["J", "Y"]:
                        edit0[3] = str(dic["jn"][int(edit[3])])
                        edit0[4] = str(dic["jn"][int(edit[4])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["i1"][int(edit[1])], dic["in"][int(edit[2])] + 1
                        ):
                            edit0[1] = str(i)
                            edit0[2] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["J-", "Y-"]:
                        edit0[3] = str(dic["j1"][int(edit[3])])
                        edit0[4] = str(dic["j1"][int(edit[4])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["i1"][int(edit[1])], dic["in"][int(edit[2])] + 1
                        ):
                            edit0[1] = str(i)
                            edit0[2] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    edit[1] = str(dic["i1"][int(edit[1])])
                    edit[2] = str(dic["in"][int(edit[2])])
                    edit[3] = str(dic["j1"][int(edit[3])])
                    edit[4] = str(dic["jn"][int(edit[4])])
                    edit[5] = str(dic["k1"][int(edit[5])])
                    edit[6] = str(dic["kn"][int(edit[6])])
                    return True
                if dic["vicinity"]:
                    if (
                        dic["ic"][int(edit[1])]
                        * dic["ic"][int(edit[2])]
                        * dic["jc"][int(edit[3])]
                        * dic["jc"][int(edit[4])]
                        * dic["kc"][int(edit[5])]
                        * dic["kc"][int(edit[6])]
                        == 0
                    ):
                        return True
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["ic"][int(edit[2])])
                edit[3] = str(dic["jc"][int(edit[3])])
                edit[4] = str(dic["jc"][int(edit[4])])
                edit[5] = str(dic["kc"][int(edit[5])])
                edit[6] = str(dic["kc"][int(edit[6])])
                dic["lol"].append(" ".join(edit))
                return True
    return False


def handle_aqucon(dic, nrwo):
    """
    Handle the modified i,j,k aquifer indices

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "AQUCON":
        dic["aqucon"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["aqucon"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["lol"].append(nrwo)
                dic["aqucon"] = False
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["refinement"]:
                    dcn = edit[7]
                    edit0 = edit.copy()
                    if dcn in ["I", "X"]:
                        edit0[1] = str(dic["in"][int(edit[1])])
                        edit0[2] = str(dic["in"][int(edit[2])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["j1"][int(edit[3])], dic["jn"][int(edit[4])] + 1
                        ):
                            edit0[3] = str(i)
                            edit0[4] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["I-", "X-"]:
                        edit0[1] = str(dic["i1"][int(edit[1])])
                        edit0[2] = str(dic["i1"][int(edit[2])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["j1"][int(edit[3])], dic["jn"][int(edit[4])] + 1
                        ):
                            edit0[3] = str(i)
                            edit0[4] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["J", "Y"]:
                        edit0[3] = str(dic["jn"][int(edit[3])])
                        edit0[4] = str(dic["jn"][int(edit[4])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["i1"][int(edit[1])], dic["in"][int(edit[2])] + 1
                        ):
                            edit0[1] = str(i)
                            edit0[2] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["J-", "Y-"]:
                        edit0[3] = str(dic["j1"][int(edit[3])])
                        edit0[4] = str(dic["j1"][int(edit[4])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["i1"][int(edit[1])], dic["in"][int(edit[2])] + 1
                        ):
                            edit0[1] = str(i)
                            edit0[2] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    edit[1] = str(dic["i1"][int(edit[1])])
                    edit[2] = str(dic["in"][int(edit[2])])
                    edit[3] = str(dic["j1"][int(edit[3])])
                    edit[4] = str(dic["jn"][int(edit[4])])
                    edit[5] = str(dic["k1"][int(edit[5])])
                    edit[6] = str(dic["kn"][int(edit[6])])
                    return True
                if dic["vicinity"]:
                    if (
                        dic["ic"][int(edit[1])]
                        * dic["ic"][int(edit[2])]
                        * dic["jc"][int(edit[3])]
                        * dic["jc"][int(edit[4])]
                        * dic["kc"][int(edit[5])]
                        * dic["kc"][int(edit[6])]
                        == 0
                    ):
                        return True
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["ic"][int(edit[2])])
                edit[3] = str(dic["jc"][int(edit[3])])
                edit[4] = str(dic["jc"][int(edit[4])])
                edit[5] = str(dic["kc"][int(edit[5])])
                edit[6] = str(dic["kc"][int(edit[6])])
                dic["lol"].append(" ".join(edit))
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


def handle_pinch(dic, nrwo):
    """
    Keep pinch from the input model

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if "PINCH" in nrwo:
        edit = nrwo.split()
        if edit[0] != "PINCH":
            return False
        dic["pinch"] = True
        dic["lol"].append(edit[0])
        return True
    if dic["pinch"]:
        edit = nrwo.split()
        if edit:
            if edit[0][:2] != "--":
                dic["lol"].append(nrwo)
                if "/" in edit[0] or "/" in edit[-1]:
                    dic["pinch"] = False
        return True
    return False


def handle_multregt(dic, nrwo):
    """
    Copy if MULTREGT is on the GRID section

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if "MULTREGT" in nrwo and "/" not in nrwo:
        edit = nrwo.split()
        if edit[0] != "MULTREGT":
            return False
        dic["multregt"] = True
        dic["lol"].append(edit[0])
        return True
    if dic["multregt"]:
        edit = nrwo.split()
        if edit:
            dic["lol"].append(nrwo)
            if edit[0] == "/":
                dic["multregt"] = False
        return True
    return False


def handle_bccon(dic, nrwo):
    """
    Handle the modified i,j,k bccon indices

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "BCCON":
        dic["bccon"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["bccon"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["lol"].append(nrwo)
                dic["bccon"] = False
                return True
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["refinement"]:
                    edit[1] = str(dic["i1"][int(edit[1])])
                    edit[2] = str(dic["in"][int(edit[2])])
                    edit[3] = str(dic["j1"][int(edit[3])])
                    edit[4] = str(dic["jn"][int(edit[4])])
                    edit[5] = str(dic["k1"][int(edit[5])])
                    edit[6] = str(dic["kn"][int(edit[6])])
                else:
                    if dic["vicinity"]:
                        if (
                            dic["ic"][int(edit[1])]
                            * dic["ic"][int(edit[2])]
                            * dic["jc"][int(edit[3])]
                            * dic["jc"][int(edit[4])]
                            * dic["kc"][int(edit[5])]
                            * dic["kc"][int(edit[6])]
                            == 0
                        ):
                            return True
                    edit[1] = str(dic["ic"][int(edit[1])])
                    edit[2] = str(dic["ic"][int(edit[2])])
                    edit[3] = str(dic["jc"][int(edit[3])])
                    edit[4] = str(dic["jc"][int(edit[4])])
                    edit[5] = str(dic["kc"][int(edit[5])])
                    edit[6] = str(dic["kc"][int(edit[6])])
                dic["lol"].append(" ".join(edit))
                return True
    return False


def handle_multiply(dic, nrwo):
    """
    Handle the modified i,j,k multiply indices

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
            if edit[0][:2] != "--":
                if dic["refinement"]:
                    edit[2] = str(dic["i1"][int(edit[2])])
                    edit[3] = str(dic["in"][int(edit[3])])
                    edit[4] = str(dic["j1"][int(edit[4])])
                    edit[5] = str(dic["jn"][int(edit[5])])
                    edit[6] = str(dic["k1"][int(edit[6])])
                    edit[7] = str(dic["kn"][int(edit[7])])
                else:
                    if dic["vicinity"]:
                        if (
                            dic["ic"][int(edit[2])]
                            * dic["ic"][int(edit[3])]
                            * dic["jc"][int(edit[4])]
                            * dic["jc"][int(edit[5])]
                            * dic["kc"][int(edit[6])]
                            * dic["kc"][int(edit[7])]
                            == 0
                        ):
                            return True
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
    Handle the modified i,j,k nnc indices

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
            if edit[0][:2] != "--":
                if dic["refinement"]:
                    edit[0] = str(dic["i1"][int(edit[0])])
                    edit[1] = str(dic["j1"][int(edit[1])])
                    edit[2] = str(dic["k1"][int(edit[2])])
                    edit[3] = str(dic["in"][int(edit[3])])
                    edit[4] = str(dic["jn"][int(edit[4])])
                    edit[5] = str(dic["kn"][int(edit[5])])
                else:
                    if dic["vicinity"]:
                        if (
                            dic["ic"][int(edit[0])]
                            * dic["jc"][int(edit[1])]
                            * dic["kc"][int(edit[2])]
                            * dic["ic"][int(edit[3])]
                            * dic["jc"][int(edit[4])]
                            * dic["kc"][int(edit[5])]
                            == 0
                        ):
                            return True
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
    Handle the modified i,j,k fault indices

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
            if edit[0][:2] != "--":
                if dic["refinement"]:
                    dcn = edit[7]
                    edit0 = edit.copy()
                    if dcn in ["I", "X"]:
                        edit0[1] = str(dic["in"][int(edit[1])])
                        edit0[2] = str(dic["in"][int(edit[2])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["j1"][int(edit[3])], dic["jn"][int(edit[4])] + 1
                        ):
                            edit0[3] = str(i)
                            edit0[4] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["I-", "X-"]:
                        edit0[1] = str(dic["i1"][int(edit[1])])
                        edit0[2] = str(dic["i1"][int(edit[2])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["j1"][int(edit[3])], dic["jn"][int(edit[4])] + 1
                        ):
                            edit0[3] = str(i)
                            edit0[4] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["J", "Y"]:
                        edit0[3] = str(dic["jn"][int(edit[3])])
                        edit0[4] = str(dic["jn"][int(edit[4])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["i1"][int(edit[1])], dic["in"][int(edit[2])] + 1
                        ):
                            edit0[1] = str(i)
                            edit0[2] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    elif dcn in ["J-", "Y-"]:
                        edit0[3] = str(dic["j1"][int(edit[3])])
                        edit0[4] = str(dic["j1"][int(edit[4])])
                        edit0[5] = str(dic["k1"][int(edit[5])])
                        edit0[6] = str(dic["kn"][int(edit[6])])
                        for i in range(
                            dic["i1"][int(edit[1])], dic["in"][int(edit[2])] + 1
                        ):
                            edit0[1] = str(i)
                            edit0[2] = str(i)
                            dic["lol"].append(" ".join(edit0))
                    edit[1] = str(dic["i1"][int(edit[1])])
                    edit[2] = str(dic["in"][int(edit[2])])
                    edit[3] = str(dic["j1"][int(edit[3])])
                    edit[4] = str(dic["jn"][int(edit[4])])
                    edit[5] = str(dic["k1"][int(edit[5])])
                    edit[6] = str(dic["kn"][int(edit[6])])
                    return True
                if dic["vicinity"]:
                    if (
                        dic["ic"][int(edit[1])]
                        * dic["ic"][int(edit[2])]
                        * dic["jc"][int(edit[3])]
                        * dic["jc"][int(edit[4])]
                        * dic["kc"][int(edit[5])]
                        * dic["kc"][int(edit[6])]
                        == 0
                    ):
                        return True
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["ic"][int(edit[2])])
                edit[3] = str(dic["jc"][int(edit[3])])
                edit[4] = str(dic["jc"][int(edit[4])])
                edit[5] = str(dic["kc"][int(edit[5])])
                edit[6] = str(dic["kc"][int(edit[6])])
                dic["lol"].append(" ".join(edit))
                return True
    return False


def handle_welsegs(dic, nrwo):
    """
    Handle the welsegs

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "WELSEGS":
        dic["welsegs"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["welsegs"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["welsegs"] = False
                if dic["skip"]:
                    dic["skip"] = False
                    return True
        if len(edit) > 1:
            if edit[0][:2] != "--" and dic["lol"][-1] == "WELSEGS":
                well = edit[0].replace("'", "")
                if well not in dic["nwells"] or well not in dic["swells"]:
                    del dic["lol"][-1]
                    if dic["lol"][-1] == "WELSEGS":
                        del dic["lol"][-1]
                    dic["skip"] = True
                    return True
            elif edit[0][:2] != "--" and not dic["skip"]:
                dic["lol"].append(nrwo)
                return True
            # if edit[0][:2] != "--" and not dic["skip"]:
            #     if edit[0] not in dic["nwells"]:
            #         del dic["lol"][-1]
            #         if dic["lol"][-1] == "WELSEGS":
            #             del dic["lol"][-1]
            #         dic["skip"] = True
            #         return True
            else:
                return True
        elif dic["skip"]:
            return True
    return False


def handle_compsegs(dic, nrwo):
    """
    Handle the compsegs

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
    if dic["compsegs"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["compsegs"] = False
                if dic["skip"]:
                    dic["skip"] = False
                    return True
        if len(edit) > 1:
            if edit[0][:2] != "--" and dic["lol"][-1] == "COMPSEGS":
                well = edit[0].replace("'", "")
                if well not in dic["nwells"]:
                    del dic["lol"][-1]
                    if dic["lol"][-1] == "COMPSEGS":
                        del dic["lol"][-1]
                    dic["skip"] = True
                    return True
            elif not dic["skip"]:
                dic["lol"].append(nrwo)
                return True
            else:
                return True
        elif dic["skip"]:
            return True
        #     if edit[0][:2] != "--" and not dic["skip"]:
        #         if edit[0] not in dic["nwells"]:
        #             del dic["lol"][-1]
        #             if dic["lol"][-1] == "COMPSEGS":
        #                 del dic["lol"][-1]
        #             dic["skip"] = True
        #             return True
        #     else:
        #         return True
        # elif dic["skip"]:
        #     return True
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
                dic["edit0"] = ""
                dic["compdat"] = False
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["vicinity"]:
                    well = edit[0].replace("'", "")
                    if (
                        well not in dic["nwells"]
                        or dic["ic"][int(edit[1])]
                        * dic["jc"][int(edit[2])]
                        * dic["kc"][int(edit[3])]
                        * dic["kc"][int(edit[4])]
                        == 0
                    ):
                        return True
                if dic["remove"] > 0 and len(edit) > 7:
                    if edit[7] != "/":
                        edit[7] = "1*"
                if dic["remove"] > 0 and len(edit) > 9:
                    if not edit[9] in ["1*", "2*", "3*", "/"]:
                        edit[9] = "1*"
                if dic["remove"] > 1 and len(edit) > 12:
                    if edit[-2] != "/":
                        edit[-2] = ""
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["jc"][int(edit[2])])
                if dic["refinement"]:
                    well = edit[0].replace("'", "")
                    if dic["edit0"]:
                        well0 = dic["edit0"][0].replace("'", "")
                        if (well == well0 and well0 not in dic["nsegw"]) and (
                            edit[1] != str(dic["ic"][int(dic["edit0"][1])])
                            or edit[2] != str(dic["jc"][int(dic["edit0"][2])])
                        ):
                            edit[3] = str(dic["kc"][int(edit[3])])
                            edit[4] = str(dic["kc"][int(edit[4])])
                            edit0 = edit.copy()
                            edit1 = edit.copy()
                            edit1[3] = str(dic["kc"][int(dic["edit0"][3])])
                            edit1[4] = str(dic["kc"][int(dic["edit0"][4])])
                            if int(edit[1]) != dic["ic"][int(dic["edit0"][1])]:
                                n = int(edit[1]) - dic["ic"][int(dic["edit0"][1])]
                                for i in range(abs(n) - 1):
                                    edit0[1] = str(
                                        dic["ic"][int(dic["edit0"][1])]
                                        + int((i + 1) * n / abs(n))
                                    )
                                    edit1[1] = str(
                                        dic["ic"][int(dic["edit0"][1])]
                                        + int((i + 1) * n / abs(n))
                                    )
                                    if i < (abs(n) - 1) / 2:
                                        dic["lol"].append(" ".join(edit1))
                                    else:
                                        dic["lol"].append(" ".join(edit0))
                            elif int(edit[2]) != dic["jc"][int(dic["edit0"][2])]:
                                n = int(edit[2]) - dic["jc"][int(dic["edit0"][2])]
                                for i in range(abs(n) - 1):
                                    edit0[2] = str(
                                        dic["jc"][int(dic["edit0"][2])]
                                        + int((i + 1) * n / abs(n))
                                    )
                                    edit1[2] = str(
                                        dic["jc"][int(dic["edit0"][2])]
                                        + int((i + 1) * n / abs(n))
                                    )
                                    if i < (abs(n) - 1) / 2:
                                        dic["lol"].append(" ".join(edit1))
                                    else:
                                        dic["lol"].append(" ".join(edit0))
                        elif (
                            well == well0
                            and well0 not in dic["nsegw"]
                            and well0 in dic["swells"]
                        ) and (
                            edit[1] == str(dic["ic"][int(dic["edit0"][1])])
                            and edit[2] == str(dic["jc"][int(dic["edit0"][2])])
                            and dic["kc"][int(edit[3])]
                            != dic["kc"][int(dic["edit0"][3])]
                        ):
                            if (
                                dic["kc"][int(dic["edit0"][3])]
                                < dic["kc"][int(edit[3])]
                            ):
                                for n in range(
                                    dic["kc"][int(dic["edit0"][3])],
                                    dic["kc"][int(edit[3])],
                                ):
                                    edit[3] = str(n + 1)
                                    edit[4] = str(n + 1)
                                    dic["lol"].append(" ".join(edit))
                            else:
                                for n in range(
                                    dic["kc"][int(edit[3])],
                                    dic["kc"][int(dic["edit0"][3])],
                                ):
                                    edit[3] = str(n + 1)
                                    edit[4] = str(n + 1)
                                    dic["lol"].append(" ".join(edit))
                            dic["edit0"] = nrwo.split()
                            return True
                        elif well in dic["swells"] + dic["nsegw"]:
                            edit[3] = str(dic["kc"][int(edit[3])])
                            edit[4] = str(dic["kc"][int(edit[4])])
                        else:
                            edit[3] = str(dic["k1"][int(edit[3])])
                            edit[4] = str(dic["kn"][int(edit[4])])
                    elif well in dic["swells"] + dic["nsegw"]:
                        edit[3] = str(dic["kc"][int(edit[3])])
                        edit[4] = str(dic["kc"][int(edit[4])])
                    else:
                        edit[3] = str(dic["k1"][int(edit[3])])
                        edit[4] = str(dic["kn"][int(edit[4])])
                else:
                    edit[3] = str(dic["kc"][int(edit[3])])
                    edit[4] = str(dic["kc"][int(edit[4])])
                dic["lol"].append(" ".join(edit))
                dic["edit0"] = nrwo.split()
                return True
    if dic["compsegs"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["compsegs"] = False
                if dic["lol"][-1].split()[0] in dic["awells"]:
                    del dic["lol"][-1]
                    del dic["lol"][-1]
                    return True
            if (
                len(edit) > 1
                and edit[0][:2] != "--"
                and dic["lol"][-1].split()[0] == "COMPSEGS"
                and dic["vicinity"]
            ):
                well = edit[0].replace("'", "")
                if well not in dic["nwells"] or well not in dic["swells"]:
                    del dic["lol"][-1]
                    del dic["lol"][-1]
                    return True
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["vicinity"]:
                    well = edit[0].replace("'", "")
                    if (well not in dic["nwells"] and len(edit) < 4) or dic["ic"][
                        int(edit[0])
                    ] * dic["jc"][int(edit[1])] * dic["kc"][int(edit[2])] == 0:
                        return True
                    else:
                        edit[0] = str(dic["ic"][int(edit[0])])
                        edit[1] = str(dic["jc"][int(edit[1])])
                        edit[2] = str(dic["kc"][int(edit[2])])
                        dic["lol"].append(" ".join(edit))
                        return True
                elif dic["refinement"]:
                    edit[0] = str(dic["ic"][int(edit[0])])
                    edit[1] = str(dic["jc"][int(edit[1])])
                    # for i in range(
                    #     dic["k1"][int(edit[2])], dic["kn"][int(edit[2])] + 1
                    # ):
                    #     edit[2] = str(i)
                    edit[2] = str(dic["kc"][int(edit[2])])
                    dic["lol"].append(" ".join(edit))
                else:
                    edit[0] = str(dic["ic"][int(edit[0])])
                    edit[1] = str(dic["jc"][int(edit[1])])
                    edit[2] = str(dic["kc"][int(edit[2])])
                    dic["lol"].append(" ".join(edit))
                return True
            else:
                return True
    if dic["complump"]:
        edit = nrwo.split()
        if edit:
            if edit[0] == "/":
                dic["complump"] = False
                if dic["lol"][-1].split()[0] in dic["awells"]:
                    del dic["lol"][-1]
                    del dic["lol"][-1]
                    return True
            if (
                len(edit) > 1
                and edit[0][:2] != "--"
                and dic["lol"][-1].split()[0] == "COMPLUMP"
                and dic["vicinity"]
            ):
                well = edit[0].replace("'", "")
                if well not in dic["nwells"] or well not in dic["swells"]:
                    del dic["lol"][-1]
                    del dic["lol"][-1]
                    return True
        if len(edit) > 2:
            if edit[0][:2] != "--":
                tmp = edit.copy()
                whr = 0
                for i, val in enumerate(tmp):
                    if "*" in val:
                        edit.pop(i + whr)
                        for _ in range(int(val[0])):
                            edit.insert(i + whr, "1*")
                        whr += int(val[0]) - 1
                if dic["vicinity"]:
                    well = edit[0].replace("'", "")
                    for val, x in zip(edit[1:5], ["i", "j", "k", "k"]):
                        if "*" not in val:
                            if dic[f"{x}c"][int(val)] == 0:
                                return True
                    if well not in dic["nwells"]:
                        return True
                    else:
                        for i, x in zip(range(1, 5), ["i", "j", "k", "k"]):
                            if "*" not in edit[i]:
                                edit[i] = str(dic[f"{x}c"][int(edit[i])])
                        dic["lol"].append(" ".join(edit))
                        return True
                else:
                    for i, x in zip(range(1, 5), ["i", "j", "k", "k"]):
                        if "*" not in edit[i]:
                            edit[i] = str(dic[f"{x}c"][int(edit[i])])
                    dic["lol"].append(" ".join(edit))
                return True
            else:
                return True
    return False


def handle_wells(dic, nrwo):
    """
    Add the necessary keywords and modified i,j,k well indices

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
                if dic["vicinity"]:
                    well = edit[0].replace("'", "")
                    if well not in dic["nwells"]:
                        return True
                    if dic["hvicinity"]:
                        if dic["ic"][int(edit[2])] == 0:
                            for i in range(dic["nx"]):
                                if dic["ic"][int(edit[2]) - i] > 0:
                                    edit[2] = str(dic["ic"][int(edit[2]) - i])
                                    break
                                if dic["ic"][int(edit[2]) + i] > 0:
                                    edit[2] = str(dic["ic"][int(edit[2]) + i])
                                    break
                        else:
                            edit[2] = str(dic["ic"][int(edit[2])])
                        if dic["jc"][int(edit[3])] == 0:
                            for i in range(dic["ny"]):
                                if dic["jc"][int(edit[3]) - i] > 0:
                                    edit[3] = str(dic["jc"][int(edit[3]) - i])
                                    break
                                if dic["ic"][int(edit[3]) + i] > 0:
                                    edit[3] = str(dic["jc"][int(edit[3]) + i])
                                    break
                        else:
                            edit[3] = str(dic["jc"][int(edit[3])])
                        dic["lol"].append(" ".join(edit))
                        return True
                    if dic["ic"][int(edit[2])] * dic["jc"][int(edit[3])] == 0:
                        return True
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
    if nrwo == "COMPLUMP":
        dic["complump"] = True
        dic["lol"].append(nrwo)
        return True
    return False


def handle_source(dic, nrwo):
    """
    Add the source keyword

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if nrwo == "SOURCE":
        dic["source"] = True
        dic["lol"].append(nrwo)
        return True
    if dic["source"]:
        edit = nrwo.split()
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["vicinity"]:
                    if (
                        dic["ic"][int(edit[0])]
                        * dic["jc"][int(edit[1])]
                        * dic["kc"][int(edit[2])]
                        == 0
                    ):
                        return True
                edit[0] = str(dic["ic"][int(edit[0])])
                edit[1] = str(dic["jc"][int(edit[1])])
                edit[2] = str(dic["kc"][int(edit[2])])
                dic["lol"].append(" ".join(edit))
                return True
        if edit:
            if edit[0] == "/":
                dic["source"] = False
    return False
