============
Introduction
============

.. image:: ./figs/pycopm.gif

This documentation describes the **pycopm** tool hosted in `https://github.com/cssr-tools/pycopm <https://github.com/cssr-tools/pycopm>`_.

Concept
-------
Simplified and flexible framework to create coarser OPM Flow geological models.

Roadmap
-------
In the initial development of the framework, the focus were two available models in `opm-tests <https://github.com/OPM/opm-tests>`_: `norne <https://github.com/OPM/opm-tests/tree/master/norne>`_ 
and `drogon <https://github.com/OPM/opm-tests/tree/master/drogon>`_, where the coarser models were used to perform history matching studies using
the Ensemble based reservoir tool `ERT <https://ert.readthedocs.io/en/latest/>`_, via a :doc:`configuration file <./configuration_file>`.

The current development of **pycopm** focuses on only creating coarser models (i.e., all needed input files to run OPM Flow) by only giving the OPM Flow input files
(i.e., avoiding the manual work to create templates as it was done for drogon and norne). This allows for flexibility to adapt the generated coarser decks in your
favourite history matching/optimization tool (e.g., `ERT <https://ert.readthedocs.io/en/latest/>`_, `PET <https://python-ensemble-toolbox.github.io/PET/>`_, `everest <https://github.com/equinor/everest>`_).

.. _overview:

Overview
--------
The current implementation supports the following executable with the argument options:

.. code-block:: bash

    pycopm -i name_of_input_file

where 

-i    The base name of the :doc:`configuration file <./configuration_file>` or the name of the deck, e.g., `DROGON.DATA`, (`input.txt` by default).
-o    The base name of the :doc:`output folder <./output_folder>` ('.'' by default, i.e., the folder where pycopm is executed).
-f    OPM Flow full path to executable or just `flow` (`flow` by default).
-c    Level of coarsening in the x, y, and z dir (`2,2,2` by default; either use this flag or the -x, -y, and -z ones).
-x    Vector of x-coarsening, e.g., if the grid has 6 cells in the x direction, then `0,2,0,2,0,2,0` would generate a coarser model with 3 cells, while `0,2,2,2,2,2,0` would generate a coarser model with 1 cell, i.e., 0 keeps the pilars while 2 removes them ('' by default),
-y    Vector of y-coarsening, see the description for -x ('' by default).
-z    Vector of z-coarsening, see the description for -x ('' by default).
-a    Use `min`, `max`, or `mode` to scale the actnum, e.g., min makes the new coarser cell inactive if at least one cell is inactive, while max makes it active it at least one cell is active (`mode` by default).
-n    Use `min`, `max`, or `mode` to scale endnum, eqlnum, fipnum, fluxnum, imbnum, miscnum, multnum, pvtnum, rocknum, and satnum (`mode` by default).
-s    Use `min`, `max`, or `mean` to scale permx, permy, permz, poro, swatinit, and all mult(-)xyz ('' by default, i.e., using the arithmetic average for permx/permy, harmonic average for permz, volume weighted mean for mult(-)xyz, and the pore volume weighted mean for the rest).
-p    Add the removed pore volume to the closest coarser cells (`0` by default, `1` to enable).
-q    Adjust the pv to the initial FGIP and FOIP from the input deck (`0` by default, `1` to enable).
-r    Remove CONFACT and KH from COMPDAT (`1`) and also remove PEQVR (`2`) (ITEM 13, the last entry) to compute the well transmisibility connections internally in OPM Flow using the grid properties (`2` by default; `0` to not remove).
-j    Tuning parameter to avoid creation of neighbouring connections in the coarser model where there are discontinuities between cells along the z direction, e.g., around faults ('' by default, i.e., nothing corrected; if need it, try with values of the order of 1).
-m    Execute a dry run on the input deck to generate the static properties ('prep'), generate only the coarse files ('deck'), only exectute a dry run on the generated coarse model ('dry'), 'prep_deck', 'deck_dry', or do all ('all') (`prep_deck` by default).
-w    Name of the generated deck ('' by default, i.e., the name of the input deck plus _PYCOPM.DATA).
-l    Added text before each generated .INC (`PYCOPM_` by default, i.e., the coarse porv is saved in PYCOPM_PORV.INC; set to '' to generate PORV.INC, PERMX.INC, etc).
-e    Use `utf8` or `ISO-8859-1` encoding to read the deck (`ISO-8859-1` by default).
-ijk  Given i,j,k indices in the input model, return the coarse i,j,k corresponding positions ('' by default; if not empty, e.g., 1,2,3 then the -m is set to deck and there will not be generation of coarse files, only the i,j,k coarse indices in the terminal).