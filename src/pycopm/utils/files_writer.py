# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""
Utiliy functions for necessary files and variables to run OPM Flow and ERT.
"""

from mako.template import Template
import numpy as np
from pycopm.utils.generate_files import write_grid, compact_format


def coarser_files(dic):
    """
    Method to write files by running mako templates

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    opm_properties(dic)
    ert_files(dic)

    # Write the schedule
    mytemplate = Template(
        filename=f"{dic['pat']}/template_scripts/{dic['field']}/schedule.mako"
    )
    var = {"dic": dic}
    filledtemplate = mytemplate.render(**var)
    with open(
        f"{dic['fol']}/preprocessing/schedule.SCH",
        "w",
        encoding="utf8",
    ) as file:
        file.write(filledtemplate)

    # Generate files from the mako templates
    var = {"dic": dic}
    mytemplate = Template(
        filename=f"{dic['pat']}/template_scripts/common/time_eval.mako"
    )
    filledtemplate = mytemplate.render(**var)
    with open(f"{dic['fol']}/jobs/time_eval.py", "w", encoding="utf8") as file:
        file.write(filledtemplate)
    var = {"dic": dic}
    mytemplate = Template(
        filename=f"{dic['pat']}/template_scripts/common/flow_eval.mako"
    )
    filledtemplate = mytemplate.render(**var)
    with open(f"{dic['fol']}/jobs/flow_eval.py", "w", encoding="utf8") as file:
        file.write(filledtemplate)

    # Write the deck for hm
    mytemplate = Template(
        filename=f"{dic['pat']}/template_scripts/{dic['field']}/deck.mako"
    )
    var = {"dic": dic}
    filledtemplate = mytemplate.render(**var)
    with open(
        f"{dic['fol']}/preprocessing/{dic['name']}_COARSER.DATA",
        "w",
        encoding="utf8",
    ) as file:
        file.write(filledtemplate)


def ert_files(dic):
    """
    Method to write the ERT deck

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    last = 0
    for i in range(len(dic["actnum_c"])):
        if dic["actnum_c"][i] == 1:
            last = i
    for i, k_c, min_max in zip(
        range(3),
        [dic["permx_c"], dic["permy_c"], dic["permz_c"]],
        [dic["permx_c_min_max"], dic["permy_c_min_max"], dic["permz_c_min_max"]],
    ):
        if dic["rock"][i][1] == 1 and dic["mode"] in ["files", "ert"]:
            var = {"dic": dic, "last": last, "k_c": k_c, "min_max": min_max, "i": i}
            mytemplate = Template(
                filename=f"{dic['pat']}/template_scripts/common/perm.mako"
            )
            filledtemplate = mytemplate.render(**var)
            with open(
                f"{dic['fol']}/parameters/{dic['rock'][i][0]}.tmpl",
                "w",
                encoding="utf8",
            ) as file:
                file.write(filledtemplate)
            mytemplate = Template(
                filename=f"{dic['pat']}/template_scripts/common/perm_priors.mako"
            )
            filledtemplate = mytemplate.render(**var)
            with open(
                f"{dic['fol']}/parameters/{dic['rock'][i][0]}_priors.data",
                "w",
                encoding="utf8",
            ) as file:
                file.write(filledtemplate)
            mytemplate = Template(
                filename=f"{dic['pat']}/template_scripts/common/perm_eval.mako"
            )
            filledtemplate = mytemplate.render(**var)
            with open(
                f"{dic['fol']}/jobs/{dic['rock'][i][0]}_eval.py",
                "w",
                encoding="utf8",
            ) as file:
                file.write(filledtemplate)
    dic["indc"] = 0
    for i in range(len(dic["LET"])):
        if (dic["LET"][i][2] == 1 and dic["mode"] in ["files", "ert"]) and dic[
            "deck"
        ] == 1:
            dic["indc"] = 1
            var = {"dic": dic, "i": i}
            mytemplate = Template(
                filename=f"{dic['pat']}/template_scripts/common/let.mako"
            )
            filledtemplate = mytemplate.render(**var)
            with open(
                f"{dic['fol']}/parameters/coeff_{str(dic['LET'][i][0])}.tmpl",
                "w",
                encoding="utf8",
            ) as file:
                file.write(filledtemplate)
            mytemplate = Template(
                filename=f"{dic['pat']}/template_scripts/common/let_priors.mako"
            )
            filledtemplate = mytemplate.render(**var)
            with open(
                f"{dic['fol']}/parameters/coeff_{str(dic['LET'][i][0])}_priors.data",
                "w",
                encoding="utf8",
            ) as file:
                file.write(filledtemplate)
    if dic["indc"] == 1:
        var = {"dic": dic}
        mytemplate = Template(
            filename=f"{dic['pat']}/template_scripts/{dic['field']}/table_eval.mako"
        )
        filledtemplate = mytemplate.render(**var)
        with open(f"{dic['fol']}/jobs/table_eval.py", "w", encoding="utf8") as file:
            file.write(filledtemplate)
    var = {"dic": dic}
    mytemplate = Template(
        filename=f"{dic['pat']}/template_scripts/{dic['field']}/{dic['obs']}.mako"
    )
    filledtemplate = mytemplate.render(**var)
    with open(
        f"{dic['fol']}/observations/{dic['obs']}.data",
        "w",
        encoding="utf8",
    ) as file:
        file.write(filledtemplate)
    var = {"dic": dic}
    mytemplate = Template(filename=f"{dic['pat']}/template_scripts/common/ert.mako")
    filledtemplate = mytemplate.render(**var)
    with open(f"{dic['fol']}/ert.ert", "w", encoding="utf8") as file:
        file.write(filledtemplate)


def opm_properties(dic):
    """
    Method to write OPM property files

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["git"] = (
        "--This file was generated by pycopm https://github.com/cssr-tools/pycopm\n"
    )
    prop = [
        "poro",
        "porv",
        "actnum",
        "ntg",
        "fluxnum",
        "satnum",
        "fipnum",
        "eqlnum",
        "permx",
        "permy",
        "permz",
    ]
    if dic["field"] == "drogon":
        prop += ["multnum", "fipzon", "pvtnum"]
    for name in prop:
        lines = compact_format("".join(f"{val:E} " for val in dic[f"{name}_c"]).split())
        lines.insert(0, name.upper() + "\n")
        lines.insert(0, dic["git"])
        lines.append("/\n")
        with open(
            f"{dic['fol']}/preprocessing/{name}.inc", "w", encoding="utf8"
        ) as file:
            file.write("".join(lines))
    lines = compact_format("".join(f"{val:E} " for val in dic["swat_c"]).split())
    lines.insert(0, "SWATINIT\n")
    lines.insert(0, dic["git"])
    lines.append("/\n")
    with open(f"{dic['fol']}/preprocessing/swatinit.inc", "w", encoding="utf8") as file:
        file.write("".join(lines))
    lines = [dic["git"]]
    for name in ["swat", "sgas", "pressure", "rs", "rv"]:
        lines += [name.upper() + "\n"]
        lines += compact_format(
            "".join(f"{val:E} " for val in dic[f"{name}_c"]).split()
        )
        lines += ["/\n"]
    with open(f"{dic['fol']}/preprocessing/init.inc", "w", encoding="utf8") as file:
        file.write("".join(lines))
    lines = compact_format("".join(f"{val:E} " for val in dic["multz_c"]).split())
    lines.insert(0, "MULTZ\n")
    lines.insert(0, dic["git"])
    lines.append("/\n")
    with open(
        f"{dic['fol']}/preprocessing/regionbarriers.inc",
        "w",
        encoding="utf8",
    ) as file:
        file.write("".join(lines))
    if dic["deck"] > 0:
        write_let_tables(dic)
    lines = [dic["git"]]
    for name in ["swl", "sgu", "swcr"]:
        lines += [name.upper() + "\n"]
        lines += compact_format(
            "".join(f"{val:E} " for val in dic[f"{name}_c"]).split()
        )
        lines += ["/\n"]
    with open(
        f"{dic['fol']}/preprocessing/endpoints.inc",
        "w",
        encoding="utf8",
    ) as file:
        file.write("".join(lines))
    grid_features(dic)


def write_let_tables(dic):
    """
    Method to write the LET saturation function tables

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    with open(
        f"{dic['fol']}/preprocessing/tables.inc",
        "w",
        encoding="utf8",
    ) as file:
        file.write(dic["git"])
        if dic["field"] == "norne":
            file.write("SWOFLET\n")
            for _ in range(dic["satnum_cmax"]):
                file.write(
                    f"0 0.0001 {max(1.1,dic['LET'][0][1])}"
                    f" {pow(10.0,dic['LET'][1][1])} {max(1.1,dic['LET'][2][1])}"
                    f" 0.5 0 0"
                    f" {max(1.0,dic['LET'][12][1])*max(1.1,dic['LET'][3][1])}"
                    f" {pow(10.0,dic['LET'][4][1])} { max(1.1,dic['LET'][5][1])}"
                    f" 1 0.69977 17.56167 0.95615 3.76138 0.03819 /\n"
                )
            for _ in range(dic["satnum_cmax"]):
                file.write(
                    f"0 0.0001 {max(1.1,dic['LET'][0][1])}"
                    f" {pow(10.0,dic['LET'][1][1])} {max(1.1,dic['LET'][2][1])}"
                    f" 0.5 0 0 {max(1.1,dic['LET'][3][1])}"
                    f" {max(0.9,dic['LET'][13][1])*pow(10.0,dic['LET'][4][1])}"
                    f" {max(1.0,dic['LET'][14][1])*max(1.1,dic['LET'][5][1])}"
                    f" 1 0.69977 17.56167 0.95615 3.76138 0.03819 /\n"
                )
            file.write("SGOFLET\n")
            for _ in range(dic["satnum_cmax"]):
                file.write(
                    f"0 0"
                    f" {max(1.0,dic['LET'][15][1])*max(1.1,dic['LET'][6][1])}"
                    f" {pow(10.0,dic['LET'][7][1])} {max(1.1,dic['LET'][8][1])}"
                    f" 0.95 0 0.0001 {max(1.1,dic['LET'][9][1])}"
                    f" {pow(10.0,dic['LET'][10][1])} {max(1.1,dic['LET'][11][1])}"
                    f" 0.99997432 1 1 1 0 0 /\n"
                )
            for _ in range(dic["satnum_cmax"]):
                file.write(
                    f"0 0 {max(1.1,dic['LET'][6][1])}"
                    f" { max(1.0,dic['LET'][16][1])*pow(10.0,dic['LET'][7][1])}"
                    f" {max(1.0,dic['LET'][17][1])*max(1.1,dic['LET'][8][1])}"
                    f" 0.95 0 0.0001 {max(1.1,dic['LET'][9][1])}"
                    f" {pow(10.0,dic['LET'][10][1])} {max(1.1,dic['LET'][11][1])}"
                    f" 0.99997432 1 1 1 0 0 /\n"
                )
        elif dic["field"] == "drogon":
            file.write("SWOFLET\n")
            for _ in range(dic["satnum_cmax"]):
                file.write(
                    f"0 0.0001 {max(1.1,dic['LET'][0][1])}"
                    f" {pow(10.0,dic['LET'][1][1])} {max(1.1,dic['LET'][2][1])}"
                    f" {dic['LET'][14][1]} 0 0"
                    f" {max(1.0,dic['LET'][12][1])*max(1.1,dic['LET'][3][1])}"
                    f" {pow(10.0,dic['LET'][4][1])} { max(1.1,dic['LET'][5][1])}"
                    f" {dic['LET'][15][1]} 0.69977 17.56167 0.95615 3.76138 0.03819 /\n"
                )
            file.write("SGOFLET\n")
            for _ in range(dic["satnum_cmax"]):
                file.write(
                    f"0 0"
                    f" {max(1.0,dic['LET'][13][1])*max(1.1,dic['LET'][6][1])}"
                    f" {pow(10.0,dic['LET'][7][1])} {max(1.1,dic['LET'][8][1])}"
                    f" {dic['LET'][16][1]} 0 0.0001 {max(1.1,dic['LET'][9][1])}"
                    f" {pow(10.0,dic['LET'][10][1])} {max(1.1,dic['LET'][11][1])}"
                    f" {dic['LET'][17][1]} 1 1 1 0 0 /\n"
                )


def grid_features(dic):
    """
    Method to write OPM grid related files

    Args:
        dic (dict): Global dictionary

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["cr"] = np.delete(dic["cr"], dic["mr"], 0)
    dic["zc"] = np.delete(dic["zc"], dic["ir"], 0)
    write_grid(dic)
    var = {"dic": dic}
    mytemplate = Template(
        filename=f"{dic['pat']}/template_scripts/{dic['field']}/fault.mako"
    )
    filledtemplate = mytemplate.render(**var)
    with open(f"{dic['fol']}/preprocessing/fault.inc", "w", encoding="utf8") as file:
        file.write(filledtemplate)

    # Write the faults
    if dic["field"] == "norne":
        # Write the local barriers
        var = {"dic": dic}
        mytemplate = Template(
            filename=f"{dic['pat']}/template_scripts/{dic['field']}/localbarriers.mako"
        )
        filledtemplate = mytemplate.render(**var)
        with open(
            f"{dic['fol']}/preprocessing/localbarriers.inc",
            "w",
            encoding="utf8",
        ) as file:
            file.write(filledtemplate)
    elif dic["field"] == "drogon":
        var = {"dic": dic}
        mytemplate = Template(
            filename=f"{dic['pat']}/template_scripts/{dic['field']}/trans.mako"
        )
        filledtemplate = mytemplate.render(**var)
        with open(
            f"{dic['fol']}/preprocessing/trans.inc",
            "w",
            encoding="utf8",
        ) as file:
            file.write(filledtemplate)
