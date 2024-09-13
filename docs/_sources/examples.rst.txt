********
Examples
********

=======================
Via configuration files
=======================

The `examples <https://github.com/cssr-tools/pycopm/blob/main/examples>`_ folder contains configuration files
to perform HM studies in drogon and norne using `ERT <https://ert.readthedocs.io/en/latest/>`_. For example, by executing inside the `example folder for drogon <https://github.com/cssr-tools/pycopm/blob/main/examples/drogon>`_:

.. code-block:: bash

    pycopm -i coarser.txt -o drogon_coarser

The following are the drogon model from `opm-tests <https://github.com/OPM/opm-tests/tree/master/drogon>`_ and coarser model generated using **pycopm**:

.. figure:: figs/drogon_coarser.png

For norne:

.. code-block:: bash

    pycopm -i input.txt -o norne_coarser

The norne GIF in the :doc:`introduction <./introduction>` was generated using the generated coarse model. 

.. _generic:

==================
Via OPM Flow decks 
==================

The current development of **pycopm** focuses on only creating coarser models (i.e., all needed input files to run OPM Flow) by using the input deck.

Hello world
-----------
For the `HELLO_WORLD.DATA <https://github.com/cssr-tools/pycopm/blob/main/tests/decks/HELLO_WORLD.DATA>`_ deck, by executing:

.. code-block:: bash

    pycopm -i HELLO_WORLD.DATA -c 5,1,5 -m all

This would generated the following:

.. figure:: figs/hello_world_1.png

    Dry run from the input cloned deck (left) and (right) coarsed model. Adding the flag -p 1 adds the remove pore volume to the neighbouring cells.

To make active the coarse cell where there is only one active cell, this can be achieve by:

.. code-block:: bash

    pycopm -i HELLO_WORLD.DATA -c 5,1,5 -m all -a max

.. figure:: figs/hello_world_2.png

    Dry run from the input cloned deck (left) and (right) coarsed model. The region numbers by default are given by the mode, e.g., use the flag -n max to keep the maximum integer.

SPE10
-----

By downloading the `SPE10_MODEL2 model <https://github.com/OPM/opm-data/tree/master/spe10model2>`_, then:

.. code-block:: bash

    pycopm -i SPE10_MODEL2.DATA -o coarser -c 4,8,2

.. figure:: figs/spe10_model2_coarser.png

    Porosity values for the (left) original and (right) coarsed SPE10 model.

Smeaheia
--------

By downloading the `Smeaheia simulation model <https://co2datashare.org/dataset/smeaheia-dataset>`_,
then:

.. code-block:: bash

    pycopm -i Statoil_Feasibility_sim_model_with_depletion_KROSS_INJ_SECTOR_20.DATA -o . -c 5,4,3 -a min -m all

will generate a coarser model 5 times in the x direction, 4 in the y direction, and 3 in the z direction, where the coarse cell is
made inactive if at least one cell is inactive (-a min).

We use our `plopm <https://github.com/cssr-tools/plopm>`_ friend to generate PNG figures:

.. code-block:: bash

    plopm -i ' STATOIL_FEASIBILITY_SIM_MODEL_WITH_DEPLETION_KROSS_INJ_SECTOR_20_PREP_PYCOPM_DRYRUN STATOIL_FEASIBILITY_SIM_MODEL_WITH_DEPLETION_KROSS_INJ_SECTOR_20_PYCOPM' -s ,,0 -v poro -subfigs 1,2 -save smeaheia -t 'Smeaheia  Coarsed smeaheia' -xunits km -xformat .0f -yunits km -yformat .0f -d 5,5.2 -suptitle 0 -c cet_rainbow_bgyrm_35_85_c69 -cbsfax 0.30,0.01,0.4,0.02 -cformat .2f

.. figure:: figs/smeia.png

    Top view of porosity values for the (left) original and (right) coarsed model (note that we also coarse on the z direction).

.. tip::
    You can install plopm by executing in the terminal: pip install git+https://github.com/cssr-tools/plopm.git.

.. note::
    In the current implementation of the **pycopm** tool, the handling of properties that require definitions of i,j,k indices 
    (e.g., FAULTS, WELLSPECS) are assumed to be define in the main .DATA deck. Then, in order to use **pycopm** for simulation models 
    where these properties are define via include files, replace those includes in the .DATA deck with the actual content of the include files.
    Here are some relevant keywords per deck section that need to be in the main input deck to coarse and not via include files:

    SECTION GRID: MAPAXES, FAULTS, MULTREGT (other keywords like MULTZ, NTG, or definitions/operations for perms and poro can be in included files since 
    permx, permy, permz, poro, porv, multx, multy, multz are read from the .INIT file)

    SECTION PROPS: EQUALS, COPY, ADD, and MULTIPLY since this involve i,j,k indices and are apply to properties such as saturation functions parameters that
    are still given in the same input format in the coarse deck. In addition, SWATINIT if used in the deck, is read from the .INIT file and output for the 
    coarse model in a new file, then one might need to give the right include path to this special case. 

    SECTION SCHEDULE: All keywords in this section must be in the input deck and no via include viles. 


Drogon
------
Following the note above, then by downloading the `DROGON model <https://github.com/OPM/opm-tests/tree/master/drogon>`_, replacing the lines in
`DROGON_HIST.DATA <https://github.com/OPM/opm-tests/blob/master/drogon/model/DROGON_HIST.DATA>`_ for the FAULTS (L127-128) and SCHEDULE (L242-243) with
the actual content of those include files, then by executing:

.. code-block:: bash

    pycopm -i DROGON_HIST.DATA -c 1,1,3 -p 1 -l C1
    pycopm -i DROGON_HIST_PYCOPM.DATA -c 1,3,1 -p 1 -j 2.5 -l C2

this would generate the following coarse model:

.. figure:: figs/drogon_generic.png

    Note that the total pore volume is conserved for the coarse model.

Here, we first coarse in the z direction, which reduces the number of cells from 31 to 11, and after we coarse in the y direction.
After trial and error, the jump (-j) is set to 2.5 to avoid generated connections across the faults. For geological models with a lot of
inactive cells and faults, this divide and conquer apporach is recommended, i.e., coarsening first in the z directon and after coarsening
in the x and y directions. In addition, we add labels (-l) C1 and C2 to differentiate between the coarse include files.

.. note::
    Add to the generated coarse deck the missing include files in the grid section related to the region operations (e.g.,
    ../include/grid/drogon.multregt for this case).

Norne
-----
By downloading the `Norne model <https://github.com/OPM/opm-tests/tree/master/norne>`_ (and replacing the needed include files as described in the previous
example), then here we create a coarser model by removing certain pilars in order to keep the main features of the geological model:

.. code-block:: bash

    pycopm -i NORNE_ATW2013.DATA -x 0,2,0,2,2,0,2,0,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,0,2,0,2,2,0,2,2,0,2,2,2,2,0 -y 0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,2,2,2,2,2,2,2,2,0 -z 0,0,2,0,0,2,2,2,2,2,02,2,2,2,2,0,0,2,0,2,2,0,0,0,0,0,0,0,0,0,0 -a min -p 1

this would generate the following coarse model:

.. figure:: figs/norne_vec.png
