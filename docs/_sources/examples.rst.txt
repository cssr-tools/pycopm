********
Examples
********

=======================
Via configuration files
=======================

Drogon
------

The `examples <https://github.com/cssr-tools/pycopm/blob/main/examples>`_ folder contains configuration files
to perform HM studies in drogon and norne. For example, by executing inside the `example folder for drogon <https://github.com/cssr-tools/pycopm/blob/main/examples/drogon>`_:

.. code-block:: bash

    pycopm -i coarser.txt -o drogon_coarser

The following are the drogon model from `opm-tests <https://github.com/OPM/opm-tests/tree/master/drogon>`_ and coarser model generated using **pycopm**:

.. figure:: figs/drogon_coarser.png


==================
Via OPM Flow decks 
==================

SPE10
-----

See/run the `test_generic_deck.py <https://github.com/cssr-tools/pycopm/blob/main/tests/test_generic_deck.py>`_ 
for an example where **pycopm** is used to coarse the 
`SPE10_MODEL2 model <https://github.com/OPM/opm-data/tree/master/spe10model2>`_ by downloading the OPM files and running:

.. code-block:: bash

    pycopm -i SPE10_MODEL2.DATA -o coarser -c 4,8,2

.. figure:: figs/spe10_model2_coarser.png

    Porosity values for the (left) original and (right) coarsed SPE10 model.

Smeaheia
--------

By downloading the `Smeaheia simulation model <https://co2datashare.org/dataset/smeaheia-dataset>`_,
then:

.. code-block:: bash

    pycopm -i Statoil_Feasibility_sim_model_with_depletion_KROSS_INJ_SECTOR_20.DATA -o . -c 5,4,3 -a mode -j 1000

will generate a coarser model 5 times in the x direction, 4 in the y direction, and 3 in the z direction, where the mode is 
used to decide if a coarser cell should be active or inactive. The jump (-j) is set to a higher value (1000) to avoid removal
of grid connections (this is a tunning value to remove generated connections between neighbours in the coarse model).

We can execute a dry run of OPM Flow to generate the grid and static variables of the coarser model:

.. code-block:: bash

    flow STATOIL_FEASIBILITY_SIM_MODEL_WITH_DEPLETION_KROSS_INJ_SECTOR_20_PYCOPM.DATA --enable-dry-run=true

We use our `plopm <https://github.com/cssr-tools/plopm>`_ friend to generate PNG figures:

.. code-block:: bash

    plopm -i STATOIL_FEASIBILITY_SIM_MODEL_WITH_DEPLETION_KROSS_INJ_SECTOR_20_PYCOPM -s ,,0

.. figure:: figs/smeia.png

    Porosity values for the (left) original and (right) coarsed model.

.. tip::
    You can install plopm by executing in the terminal: pip install git+https://github.com/cssr-tools/plopm.git.

.. note::
    In the current implementation of the **pycopm** tool, the handling of properties that require definitions of i,j,k indices 
    (e.g., FAULTS, WELLSPECS) are assumed to be define in the main .DATA deck. Then, in order to use **pycopm** for simulation models 
    where these properties are define via include files, replace those includes in the .DATA deck with the actual content of the include files.