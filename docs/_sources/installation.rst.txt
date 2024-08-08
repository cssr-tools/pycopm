============
Installation
============

Python package
--------------

To install the **pycopm** executable in an existing Python environment: 

.. code-block:: bash

    pip install git+https://github.com/cssr-tools/pycopm.git

If you are interested in modifying the source code, then you can clone the repository and 
install the Python requirements in a virtual environment with the following commands:

.. code-block:: console

    # Clone the repo
    git clone https://github.com/cssr-tools/pycopm.git
    # Get inside the folder
    cd pycopm
    # Create virtual environment
    python3 -m venv vpycopm
    # Activate virtual environment
    source vpycopm/bin/activate
    # Upgrade pip, setuptools, and wheel
    pip install --upgrade pip setuptools wheel
    # Install the pycopm package
    pip install -e .
    # For contributions/testing/linting, install the dev-requirements
    pip install -r dev-requirements.txt

OPM Flow
--------
You also need to install:

* OPM Flow (https://opm-project.org, Release 2024.04 or current master branches)

.. tip::

    See the `CI.yml <https://github.com/cssr-tools/pycopm/blob/main/.github/workflows/CI.yml>`_ script 
    for installation of OPM Flow (binary packages) and the pycopm package in Linux. 

Source build in Linux/Windows
+++++++++++++++++++++++++++++
If you are a Linux user (including the Windows subsystem for Linux), then you could try to build Flow (after installing the `prerequisites <https://opm-project.org/?page_id=239>`_) from the master branches with mpi support by running
in the terminal the following lines (which in turn should build flow in the folder ./build/opm-simulators/bin/flow.): 

.. code-block:: console

    CURRENT_DIRECTORY="$PWD"

    for repo in common grid models simulators
    do
        git clone https://github.com/OPM/opm-$repo.git
    done

    mkdir build

    for repo in common grid models
    do
        mkdir build/opm-$repo
        cd build/opm-$repo
        cmake -DUSE_MPI=1 -DWITH_NDEBUG=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CURRENT_DIRECTORY/build/opm-common;$CURRENT_DIRECTORY/build/opm-grid" $CURRENT_DIRECTORY/opm-$repo
        make -j5 opm$repo
        cd ../..
    done    

    mkdir build/opm-simulators
    cd build/opm-simulators
    cmake -DUSE_MPI=1 -DWITH_NDEBUG=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CURRENT_DIRECTORY/build/opm-common;$CURRENT_DIRECTORY/build/opm-grid;$CURRENT_DIRECTORY/build/opm-models" $CURRENT_DIRECTORY/opm-simulators
    make -j5 flow
    cd ../..


.. tip::

    You can create a .sh file (e.g., build_opm_mpi.sh), copy the previous lines, and run in the terminal **source build_opm_mpi.sh**  

Source build in macOS
+++++++++++++++++++++
For macOS, there are no available binary packages, so OPM Flow needs to be built from source, in addition to the dune libraries 
(see the `prerequisites <https://opm-project.org/?page_id=239>`_, which can be installed using macports or brew). This can be achieved by the following lines:

.. code-block:: console

    CURRENT_DIRECTORY="$PWD"

    for module in common geometry grid istl
    do   git clone https://gitlab.dune-project.org/core/dune-$module.git --branch v2.9.1
    done
    for module in common geometry grid istl
    do   ./dune-common/bin/dunecontrol --only=dune-$module cmake -DCMAKE_DISABLE_FIND_PACKAGE_MPI=1
         ./dune-common/bin/dunecontrol --only=dune-$module make -j5
    done

    for repo in common grid models simulators
    do
        git clone https://github.com/OPM/opm-$repo.git
    done

    mkdir build

    for repo in common grid models
    do
        mkdir build/opm-$repo
        cd build/opm-$repo
        cmake -DUSE_MPI=0 -DWITH_NDEBUG=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CURRENT_DIRECTORY/dune-common/build-cmake;$CURRENT_DIRECTORY/dune-grid/build-cmake;$CURRENT_DIRECTORY/dune-geometry/build-cmake;$CURRENT_DIRECTORY/dune-istl/build-cmake;$CURRENT_DIRECTORY/build/opm-common;$CURRENT_DIRECTORY/build/opm-grid" $CURRENT_DIRECTORY/opm-$repo
        make -j5 opm$repo
        cd ../..
    done    

    mkdir build/opm-simulators
    cd build/opm-simulators
    cmake -DUSE_MPI=0 -DWITH_NDEBUG=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CURRENT_DIRECTORY/dune-common/build-cmake;$CURRENT_DIRECTORY/dune-grid/build-cmake;$CURRENT_DIRECTORY/dune-geometry/build-cmake;$CURRENT_DIRECTORY/dune-istl/build-cmake;$CURRENT_DIRECTORY/build/opm-common;$CURRENT_DIRECTORY/build/opm-grid;$CURRENT_DIRECTORY/build/opm-models" $CURRENT_DIRECTORY/opm-simulators
    make -j5 flow
    cd ../..

In addition, use at least a Python version of 3.10 (due to the resdata Python package).