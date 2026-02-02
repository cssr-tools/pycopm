============
Installation
============

The following steps work installing the dependencies in Ubuntu via apt-get or in macOS using `brew <https://brew.sh>`_ or `macports <https://www.macports.org>`_.
While using package managers such as Anaconda, Miniforge, or Mamba might work, these are not tested.
The supported Python versions are 3.11 to 3.13. We will update the documentation when Python3.14 is supported
(e.g., the ert Python package is not yet available via pip install in Python 3.14).

.. note::

    In Ubuntu, one also needs to install freeglut3-dev:

    .. code-block:: bash
        
        sudo apt-get install freeglut3-dev

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

* OPM Flow (https://opm-project.org, Release 2025.10 or current master branches)

Binary packages
+++++++++++++++

See the `downloading and installing <https://opm-project.org/?page_id=36>`_ OPM Flow online documentation for 
instructions to install the binary packages in Ubuntu and Red Hat Enterprise Linux, and for other platforms which are
supported either via source builds or through running a virtual machine.

.. tip::

    See the `ci_pycopm_ubuntu.yml <https://github.com/cssr-tools/pycopm/blob/main/.github/workflows/ci_pycopm_ubuntu.yml>`_ script 
    for installation of OPM Flow (binary packages) and the pycopm package in Ubuntu.

Source build in Linux/Windows
+++++++++++++++++++++++++++++
If you are a Linux user (including the Windows subsystem for Linux, see `this link <https://learn.microsoft.com/en-us/windows/python/web-frameworks>`_ 
for a nice tutorial for setting Python environments in WSL), then you could try to build Flow (after installing the `prerequisites <https://opm-project.org/?page_id=239>`_) from the master branches with mpi support by running
in the terminal the following lines (which in turn should build flow in the folder ./build/opm-simulators/bin/flow): 

.. code-block:: console

    CURRENT_DIRECTORY="$PWD"

    mkdir build

    for repo in common grid simulators
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

Brew formula for macOS
++++++++++++++++++++++
For macOS, there are no available binary packages, so OPM Flow needs to be built from source. Recently, a formula to build flow using brew has
been added in `https://github.com/cssr-tools/homebrew-opm <https://github.com/cssr-tools/homebrew-opm>`_. 
Then, you can try to install flow (v2025.10) by simply typing:

.. code-block:: console

    brew install cssr-tools/opm/opm-simulators

You can check if the installation of OPM Flow succeded by typing in the terminal **flow \-\-help**.

.. tip::
    See the actions in the `cssr-tools/homebrew-opm <https://github.com/cssr-tools/homebrew-opm/actions>`_ repository.

Source build in macOS
+++++++++++++++++++++
If you would like to build the latest OPM Flow from the master branch, then you can first install the prerequisites using brew:

.. code-block:: console

    brew install cjson boost openblas suite-sparse python@3.13 cmake 

In addition, it is recommended to uprade and update your macOS to the latest available versions (the following steps have 
worked for macOS Tahoe 26.2.0 with Apple clang version 17.0.0). After the prerequisites are installed, then building OPM Flow
can be achieved with the following bash lines:

.. code-block:: console

    CURRENT_DIRECTORY="$PWD"

    for module in common geometry grid istl
    do  git clone https://gitlab.dune-project.org/core/dune-$module.git
        cd dune-$module && git checkout v2.10.0 && cd ..
        ./dune-common/bin/dunecontrol --only=dune-$module cmake -DCMAKE_DISABLE_FIND_PACKAGE_MPI=1
        ./dune-common/bin/dunecontrol --only=dune-$module make -j5
    done

    mkdir build

    for repo in common grid simulators
    do  git clone https://github.com/OPM/opm-$repo.git
        mkdir build/opm-$repo && cd build/opm-$repo
        cmake -DUSE_MPI=0 -DWITH_NDEBUG=1 -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$CURRENT_DIRECTORY/dune-common/build-cmake;$CURRENT_DIRECTORY/dune-grid/build-cmake;$CURRENT_DIRECTORY/dune-geometry/build-cmake;$CURRENT_DIRECTORY/dune-istl/build-cmake;$CURRENT_DIRECTORY/build/opm-common;$CURRENT_DIRECTORY/build/opm-grid" $CURRENT_DIRECTORY/opm-$repo
        if [[ $repo == simulators ]]; then
            make -j5 flow
        else
            make -j5 opm$repo
        fi
        cd ../..
    done

    echo "export PATH=\$PATH:$CURRENT_DIRECTORY/build/opm-simulators/bin" >> ~/.zprofile
    source ~/.zprofile

This builds OPM Flow, and it exports the path to the flow executable.

.. tip::
    See `this repository <https://github.com/daavid00/OPM-Flow_macOS>`_ dedicated to build OPM Flow from source in the latest macOS (GitHub actions), and tested with **pycopm**.
    If you still face problems, raise an issue in the GitHub repository, or you could also send an email to the maintainers.
