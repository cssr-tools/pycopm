[![Build Status](https://github.com/cssr-tools/pycopm/actions/workflows/CI.yml/badge.svg)](https://github.com/cssr-tools/pycopm/actions/workflows/CI.yml)
<a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%20to%203.12-blue.svg"></a>
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
<img src="docs/text/figs/pycopm.png" width="900" height="380">

# pycopm: An open-source tool to tailor OPM Flow geological models. 

## Main feature
Creation of OPM Flow geological models from provided input decks with options for grid refinement, grid coarsening, submodels, and transformations including scalings, rotations, and translations.   

## Installation
You will first need to install
* OPM Flow (https://opm-project.org, Release 2024.10 or current master branches)

To install the _pycopm_ executable from the development version:

```bash
pip install git+https://github.com/cssr-tools/pycopm.git
```

If you are interested in a specific version (e.g., v2024.10) or in modifying the source code, then you can clone the repository and install the Python requirements in a virtual environment with the following commands:

```bash
# Clone the repo
git clone https://github.com/cssr-tools/pycopm.git
# Get inside the folder
cd pycopm
# For a specific version (e.g., v2024.10), or skip this step (i.e., edge version)
git checkout v2024.10
# Create virtual environment (to specific Python, python3.12 -m venv vpycopm)
python3 -m venv vpycopm
# Activate virtual environment
source vpycopm/bin/activate
# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel
# Install the pycopm package
pip install -e .
# For contributions/testing/linting, install the dev-requirements
pip install -r dev-requirements.txt
``` 

See the [_installation_](https://cssr-tools.github.io/pycopm/installation.html) for further details on building OPM Flow from the master branches in Linux, Windows, and macOS, as well as the opm Python package.

## Running pycopm
You can run _pycopm_ as a single command line:
```
pycopm -i name_of_input_file
```
Run `pycopm --help` to see all possible command line argument options.

## Getting started
See the [_examples_](https://cssr-tools.github.io/pycopm/examples.html) in the [_documentation_](https://cssr-tools.github.io/pycopm/introduction.html).

## Citing

* Landa-Marbán, D. pycopm: An open-source tool to tailor OPM Flow geological models. Submitted.

## Publications
The following is a list of manuscripts in which _pycopm_ is used:

1. Sandve, T.H., Lorentzen, R.J., Landa-Marbán, D., Fossum, K., 2024. Closed-loop reservoir management using fast data-calibrated coarse models. European Association of Geoscientists & Engineers, ECMOR 2024, Volume 202, ISSN 2214-4609. https://doi.org/10.3997/2214-4609.202437071.

## About pycopm
The _pycopm_ package is being funded by the [_Center for Sustainable Subsurface Resources (CSSR)_](https://cssr.no) 
[project no. 331841] and by [_Expansion of Resources for CO2 Storage on the Horda Platform (ExpReCCS)_](https://www.norceresearch.no/en/projects/expansion-of-resources-for-co2-storage-on-the-horda-platform-expreccs) [project no. 336294].
Contributions are more than welcome using the fork and pull request approach.
For a new feature, please request this by raising an issue.