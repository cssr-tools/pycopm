============
Installation
============

The following steps work installing the dependencies in Ubuntu via apt-get or in macOS using brew or macports.
While using package managers such as Anaconda, Miniforge, or Mamba might work, these are not tested.
The supported Python versions are 3.11 to 3.13. We will update the documentation when Python3.14 is supported
(e.g., the resdata Python package is not yet available via pip install in Python 3.14).

.. _vpycopm:

Python package
--------------

To install the **pycopm** executable from the development version: 

.. code-block:: bash

    pip install git+https://github.com/cssr-tools/pycopm.git

If you are interested in a specific version (e.g., v2025.04) or in modifying the source code, then you can clone the repository and 
install the Python requirements in a virtual environment with the following commands:

.. code-block:: console

    # Clone the repo
    git clone https://github.com/cssr-tools/pycopm.git
    # Get inside the folder
    cd pycopm
    # For a specific version (e.g., v2025.04), or skip this step (i.e., edge version)
    git checkout v2025.04
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

.. tip::

    Typing **git tag -l** writes all available specific versions.

.. _opmflow:

OPM Flow
--------
You also need to install:

* OPM Flow (https://opm-project.org, Release 2025.04 or current master branches)

.. tip::

    See the `ci_pycopm_ubuntu.yml <https://github.com/cssr-tools/pycopm/blob/main/.github/workflows/ci_pycopm_ubuntu.yml>`_ script 
    for installation of OPM Flow (binary packages) and the pycopm package in Ubuntu.

.. note::

    For not macOS users, to install the optional Python opm package (this is an alternative
    to `resdata <https://github.com/equinor/resdata>`_, both are use to read OPM output files; while resdata is easier to
    install in macOS, opm seems to be faster; the default is `-u resdata`), execute in the terminal

    **pip install opm**

    This is equivalent to execute **pip install -e .[opm]** in the installation process.

    For macOS users, see :ref:`macOS`.

Source build in Linux/Windows
+++++++++++++++++++++++++++++
If you are a Linux user (including the Windows subsystem for Linux, see `this link <https://learn.microsoft.com/en-us/windows/python/web-frameworks>`_ 
for a nice tutorial for setting Python environments in WSL), then you could try to build Flow (after installing the `prerequisites <https://opm-project.org/?page_id=239>`_) from the master branches with mpi support by running
in the terminal the following lines (which in turn should build flow in the folder ./build/opm-simulators/bin/flow): 

.. code-block:: console

    CURRENT_DIRECTORY="$PWD"

    mkdir build

    for repo in common grid
    do  git clone https://github.com/OPM/opm-$repo.git
        mkdir build/opm-$repo
        cd build/opm-$repo
        cmake -DUSE_MPI=1 -DWITH_NDEBUG=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CURRENT_DIRECTORY/build/opm-common;$CURRENT_DIRECTORY/build/opm-grid" $CURRENT_DIRECTORY/opm-$repo
        if [[ $repo == simulators ]]; then
            make -j5 flow
        else
            make -j5 opm$repo
        fi
        cd ../..
    done


.. tip::

    You can create a .sh file (e.g., build_opm_mpi.sh), copy the previous lines, and run in the terminal **source build_opm_mpi.sh**  

.. _macOS:

Source build in macOS
+++++++++++++++++++++
For macOS, there are no available binary packages, so OPM Flow needs to be built from source, in addition to the dune libraries 
(see the `prerequisites <https://opm-project.org/?page_id=239>`_, which can be installed using macports or brew). For example,
with brew the prerequisites can be installed by:

.. code-block:: console

    brew install boost@1.85 cmake openblas suite-sparse python@3.13

.. note::
    boost 1.89.0 was made available recently (August 14th, 2025), which it is not compatible with OPM Flow (yet).
    Then, we install boost 1.85, and add the cmake path to the boost include folder, as shown in the bash lines below. 

In addition, it is recommended to uprade and update your macOS to the latest available versions (the following steps have 
worked for macOS Tahoe 26.0.1 with Apple clang version 17.0.0).
After the prerequisites are installed and the vpyocpm Python environment is created (see :ref:`vpycopm`), 
then building OPM Flow and the opm Python package can be achieved with the following bash lines:

.. code-block:: console

    CURRENT_DIRECTORY="$PWD"

    deactivate
    source vpycopm/bin/activate

    for module in common geometry grid istl
    do   git clone https://gitlab.dune-project.org/core/dune-$module.git --branch v2.9.1
        ./dune-common/bin/dunecontrol --only=dune-$module cmake -DCMAKE_DISABLE_FIND_PACKAGE_MPI=1
        ./dune-common/bin/dunecontrol --only=dune-$module make -j5
    done

    mkdir build

    for repo in common grid simulators
    do  git clone https://github.com/OPM/opm-$repo.git
        mkdir build/opm-$repo
        cd build/opm-$repo
        cmake -DPYTHON_EXECUTABLE=$(which python) -DOPM_ENABLE_PYTHON=ON -DWITH_NDEBUG=1 -DUSE_MPI=0 -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/opt/homebrew/opt/boost@1.85/include;$CURRENT_DIRECTORY/dune-common/build-cmake;$CURRENT_DIRECTORY/dune-grid/build-cmake;$CURRENT_DIRECTORY/dune-geometry/build-cmake;$CURRENT_DIRECTORY/dune-istl/build-cmake;$CURRENT_DIRECTORY/build/opm-common;$CURRENT_DIRECTORY/build/opm-grid" $CURRENT_DIRECTORY/opm-$repo
        if [[ $repo == common ]]; then
            make -j5 opm$repo
            make -j5 opmcommon_python
        elif [[ $repo == simulators ]]; then
            make -j5 flow
        else
            make -j5 opm$repo
        fi
        cd ../..
    done

    echo "export PYTHONPATH=\$PYTHONPATH:$CURRENT_DIRECTORY/build/opm-common/python" >> $CURRENT_DIRECTORY/vpycopm/bin/activate
    echo "export PATH=\$PATH:$CURRENT_DIRECTORY/build/opm-simulators/bin" >> $CURRENT_DIRECTORY/vpycopm/bin/activate

    deactivate
    source vpycopm/bin/activate

This builds OPM Flow as well as the OPM Python library, and it exports the required PYTHONPATH to the opm Python package and the path to the flow executable.

.. note::
    You can test if flow works by typing in the terminal `./build/opm-simulators/bin/flow --help`. In addition, you can add `build/opm-simulators/bin` to your path 
    to execute it as flow. You can also test that the Python package opm works by executing `python -c "import opm"`. If for any reason the installation of the Python 
    opm package was not sucessful, still all functionality of **pycopm** is available, just do not execute **pycopm** with the flag `-u opm` (see the note in 
    :ref:`opmflow` for a brief comment about the Python packages resdata and opm).

.. tip::
    See `this repository <https://github.com/daavid00/OPM-Flow_macOS>`_ dedicated to build OPM Flow from source in the latest macOS (GitHub actions), and tested with **pycopm**.
    If you still face problems, raise an issue in the GitHub repository, or you could also send an email to the maintainers.
