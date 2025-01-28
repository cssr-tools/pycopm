# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0912,R0913,R0914,R0915,C0302,R0917,R1702,R0916,R0911

"""
Methods to parser OPM decks.
"""

import csv


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
    dic["multregt"] = False
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
    dic["dimens"] = False
    dic["welldims"] = False
    dic["edit0"] = ""
    dic["nsegw"] = []
    if dic["refinement"]:
        names_segwells(dic)
    with open(dic["deck"] + ".DATA", "r", encoding=dic["encoding"]) as file:
        for row in csv.reader(file):
            nrwo = str(row)[2:-2].strip()
            if 0 < nrwo.find("\\t"):
                nrwo = nrwo.replace("\\t", " ")
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
            if nrwo == "COMPSEGS":
                dic["compsegs"] = True
                continue
            if dic["compsegs"]:
                edit = nrwo.split()
                if len(edit) > 1:
                    if edit[0][:2] != "--":
                        dic["nsegw"].append(str(edit[0]))
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
            if edit[0] != "--":
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
            if edit[0] != "--":
                if len(edit) > 2:
                    edit[1] = str(dic["nz"])
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
        dic["lol"].append(nrwo)
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
        dic["lol"].append(nrwo)
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
        # if handle_oper(dic, nrwo):
        #    return True
        if dic["trans"] == 0:
            if handle_multregt(dic, nrwo):
                return True
            if handle_multflt(dic, nrwo):
                return True
            if nrwo == "EDIT":
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


def handle_multregt(dic, nrwo):
    """
    Copy if MULTREGT is on the GRID section

    Args:
        dic (dict): Global dictionary\n
        nrwo (list): Splited row from the input deck

    Returns:
        dic (dict): Modified global dictionary

    """
    if "MULTREGT" in nrwo:
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
            if edit[-1] == "/" or edit[0] == "/":
                dic["multregt"] = False
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
                if dic["refinement"]:
                    edit[2] = str(dic["i1"][int(edit[2])])
                    edit[3] = str(dic["in"][int(edit[3])])
                    edit[4] = str(dic["j1"][int(edit[4])])
                    edit[5] = str(dic["jn"][int(edit[5])])
                    edit[6] = str(dic["k1"][int(edit[6])])
                    edit[7] = str(dic["kn"][int(edit[7])])
                else:
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
                if dic["refinement"]:
                    edit[0] = str(dic["i1"][int(edit[0])])
                    edit[1] = str(dic["j1"][int(edit[1])])
                    edit[2] = str(dic["k1"][int(edit[2])])
                    edit[3] = str(dic["in"][int(edit[3])])
                    edit[4] = str(dic["jn"][int(edit[4])])
                    edit[5] = str(dic["kn"][int(edit[5])])
                else:
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
                # if dic["refinement"]:
                #     edit[1] = str(dic["i1"][int(edit[1])])
                #     edit[2] = str(dic["in"][int(edit[2])])
                #     edit[3] = str(dic["j1"][int(edit[3])])
                #     edit[4] = str(dic["jn"][int(edit[4])])
                #     edit[5] = str(dic["k1"][int(edit[5])])
                #     edit[6] = str(dic["kn"][int(edit[6])])
                # else:
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
                dic["edit0"] = ""
                dic["compdat"] = False
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["remove"] > 0 and len(edit) > 7:
                    edit[7] = "1*"
                if dic["remove"] > 0 and len(edit) > 9:
                    edit[9] = "1*"
                if dic["remove"] > 1 and len(edit) > 12:
                    edit[-2] = ""
                edit[1] = str(dic["ic"][int(edit[1])])
                edit[2] = str(dic["jc"][int(edit[2])])
                if dic["refinement"]:
                    if dic["edit0"]:
                        if (
                            edit[0] == dic["edit0"][0]
                            and dic["edit0"][0] not in dic["nsegw"]
                        ) and (
                            edit[1] != str(dic["ic"][int(dic["edit0"][1])])
                            or edit[2] != str(dic["jc"][int(dic["edit0"][2])])
                        ):
                            edit[3] = str(dic["kn"][int(edit[4])])
                            edit[4] = str(dic["kn"][int(edit[4])])
                            edit0 = edit.copy()
                            if int(edit[1]) != dic["ic"][int(dic["edit0"][1])]:
                                n = int(edit[1]) - dic["ic"][int(dic["edit0"][1])]
                                for i in range(abs(n) - 1):
                                    edit0[1] = str(
                                        dic["ic"][int(dic["edit0"][1])]
                                        + int((i + 1) * n / abs(n))
                                    )
                                    dic["lol"].append(" ".join(edit0))
                            elif int(edit[2]) != dic["jc"][int(dic["edit0"][2])]:
                                n = int(edit[2]) - dic["jc"][int(dic["edit0"][2])]
                                for i in range(abs(n) - 1):
                                    edit0[2] = str(
                                        dic["jc"][int(dic["edit0"][2])]
                                        + int((i + 1) * n / abs(n))
                                    )
                                    dic["lol"].append(" ".join(edit0))
                        else:
                            edit[3] = str(dic["k1"][int(edit[3])])
                            edit[4] = str(dic["kn"][int(edit[4])])
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
        if len(edit) > 2:
            if edit[0][:2] != "--":
                if dic["refinement"]:
                    edit[0] = str(dic["ic"][int(edit[0])])
                    edit[1] = str(dic["jc"][int(edit[1])])
                    for i in range(
                        dic["k1"][int(edit[2])], dic["kn"][int(edit[2])] + 1
                    ):
                        edit[2] = str(i)
                        dic["lol"].append(" ".join(edit))
                else:
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
