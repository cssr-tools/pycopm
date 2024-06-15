# SPDX-FileCopyrightText: 2024 NORCE
# SPDX-License-Identifier: GPL-3.0

"""pycopm: An open-source coarsening framework using OPM Flow"""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf8") as file:
    long_description = file.read()

with open("requirements.txt", "r", encoding="utf8") as file:
    install_requires = file.read().splitlines()

with open("dev-requirements.txt", "r", encoding="utf8") as file:
    dev_requires = file.read().splitlines()

setup(
    name="pycopm",
    version="2024.04",
    install_requires=install_requires,
    extras_require={"dev": dev_requires},
    setup_requires=["setuptools_scm"],
    description="Open-source workflow for coarser simulations in OPM",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dmar/pycopm",
    author="David Landa-Marbán, Tor Harald Sandve",
    mantainer="David Landa-Marbán, Tor Harald Sandve",
    mantainer_email="dmar@norceresearch.no, tosa@norceresearch.no",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    keywords="OPM coarsening CFD CO2 H2 CCS",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    license="GPL-3.0",
    python_requires=">=3.8, <4",
    entry_points={
        "console_scripts": [
            "pycopm=pycopm.core.pycopm:main",
        ]
    },
    include_package_data=True,
)
