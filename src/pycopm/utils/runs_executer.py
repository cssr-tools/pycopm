# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""
Utiliy functions to run the studies.
"""

import os
import subprocess
from mako.template import Template


def simulations(dic):
    """Function to run OPM Flow or selected ERT functionality"""
    os.system(f"cp -a {dic['pat']}/jobs/. {dic['exe']}/{dic['fol']}/jobs/.")
    os.chdir(f"{dic['exe']}/{dic['fol']}")
    for fil in [
        "PERMX_eval",
        "PERMY_eval",
        "PERMZ_eval",
        "table_eval",
        "time_eval",
    ]:
        if os.path.exists("jobs/" + fil + ".py") == 1:
            os.system(f"chmod u+x jobs/{fil}.py")

    if dic["study"] == 0:
        os.system("ert test_run ert.ert & wait")
        if dic["mpi"] > 1:
            os.system(
                f"mpirun -np {dic['mpi']} {dic['flow']}"
                f" --parameter-file={dic['exe']}/{dic['fol']}/preprocessing/flags.param"
                f" {dic['exe']}/{dic['fol']}/output/simulations/realisation-0/iter-0/"
                f"{dic['name']}_COARSER.DATA --output-dir={dic['exe']}/{dic['fol']}/"
                f"output/simulations/realisation-0/iter-0 & wait\n"
            )
        else:
            os.system(
                f"{dic['flow']} --parameter-file={dic['exe']}/{dic['fol']}/preprocessing/"
                f"flags.param {dic['exe']}/{dic['fol']}/output/simulations/realisation-0/"
                f"iter-0/{dic['name']}_COARSER.DATA --output-dir={dic['exe']}/{dic['fol']}/"
                f"output/simulations/realisation-0/iter-0 & wait\n"
            )
        os.chdir(f"{dic['exe']}/{dic['fol']}/output/simulations/realisation-0/iter-0")
        os.chdir(f"{dic['exe']}/{dic['fol']}")
    else:
        os.system(f"ert {dic['fert'][0]} ert.ert & wait")


def plotting(dic, time):
    """Function to generate and run the plotting.py file"""
    dic["Ne"] = len(next(os.walk(f"{dic['exe']}/{dic['fol']}/output/simulations"))[1])
    dic["Ni"] = 1
    for i in range(dic["Ne"]):
        dic["Ni"] = max(
            dic["Ni"],
            len(
                next(
                    os.walk(
                        f"{dic['exe']}/{dic['fol']}/output/simulations/realisation-{i}"
                    )
                )[1]
            ),
        )
    dic["LET"] = sorted(dic["LET"], key=lambda x: x[0])
    var = {"dic": dic, "time": time}
    mytemplate = Template(
        filename=dic["pat"] + "/template_scripts/common/plot_post.mako"
    )
    filledtemplate = mytemplate.render(**var)
    with open(
        f"{dic['exe']}/{dic['fol']}/jobs/plotting.py", "w", encoding="utf8"
    ) as file:
        file.write(filledtemplate)
    task = subprocess.run(
        ["python", f"{dic['exe']}/{dic['fol']}/jobs/plotting.py"], check=True
    )
    if task.returncode != 0:
        raise ValueError(f"Invalid result: { task.returncode }")
