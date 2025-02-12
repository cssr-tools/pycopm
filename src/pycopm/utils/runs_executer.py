# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""
Utiliy functions to run the studies from toml configuration files.
"""

import os
import subprocess
from mako.template import Template


def simulations(dic):
    """
    Run OPM Flow or selected ERT functionality

    Args:
        dic (dict): Global dictionary

    Returns:
        None

    """
    os.system(f"cp -a {dic['pat']}/jobs/. {dic['fol']}/jobs/.")
    os.chdir(f"{dic['fol']}")
    for fil in [
        "PERMX_eval",
        "PERMY_eval",
        "PERMZ_eval",
        "table_eval",
        "time_eval",
        "flow_eval",
    ]:
        if os.path.exists("jobs/" + fil + ".py") == 1:
            os.system(f"chmod u+x jobs/{fil}.py")

    if dic["mode"] == "single-run":
        os.system("ert test_run ert.ert & wait")
        os.system(
            f"{dic['flow']} {dic['fol']}/output/simulations/realisation-0/"
            f"iter-0/{dic['name']}_COARSER.DATA --output-dir={dic['fol']}/"
            f"output/simulations/realisation-0/iter-0 & wait\n"
        )
        os.chdir(f"{dic['fol']}")
    elif dic["mode"] == "ert":
        os.system(f"ert {dic['ert'][0]} ert.ert & wait")


def plotting(dic, time):
    """
    Generate and run the plotting.py file

    Args:
        dic (dict): Global dictionary
        time (float): Current execution time

    Returns:
        dic (dict): Modified global dictionary

    """
    dic["net"] = len(next(os.walk(f"{dic['fol']}/output/simulations"))[1])
    dic["Ni"] = 1
    for i in range(dic["net"]):
        dic["Ni"] = max(
            dic["Ni"],
            len(next(os.walk(f"{dic['fol']}/output/simulations/realisation-{i}"))[1]),
        )
    dic["LET"] = sorted(dic["LET"], key=lambda x: x[0])
    var = {"dic": dic, "time": time}
    mytemplate = Template(
        filename=dic["pat"] + "/template_scripts/common/plot_post.mako"
    )
    filledtemplate = mytemplate.render(**var)
    with open(f"{dic['fol']}/jobs/plotting.py", "w", encoding="utf8") as file:
        file.write(filledtemplate)
    task = subprocess.run(["python", f"{dic['fol']}/jobs/plotting.py"], check=True)
    if task.returncode != 0:
        raise ValueError(f"Invalid result: { task.returncode }")
