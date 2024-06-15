********
Examples
********

==================
Configuration file 
==================

The `examples <https://github.com/cssr-tools/pycopm/blob/main/examples>`_ folder contains configuration files
to perform HM studies in drogon and norne. For example, by executing inside the `example folder for drogon <https://github.com/cssr-tools/pycopm/blob/main/examples/drogon>`_:

.. code-block:: bash

    pycopm -i coarser.txt -o drogon_coarser

The following are the drogon model from `opm-tests <https://github.com/OPM/opm-tests/tree/master/drogon>`_ and coarser model generated using **pycopm**:

.. figure:: figs/drogon_coarser.png


==========
Input deck 
==========

See/run the `test_generic_deck.py <https://github.com/cssr-tools/pycopm/blob/main/tests/test_generic_deck.py>`_ 
for an example where **pycopm** is used to coarse the 
`SPE10_MODEL2 model <https://github.com/OPM/opm-data/tree/master/spe10model2>`_ by downloading the files and running:

.. code-block:: bash

    pycopm -i SPE10_MODEL2.DATA -o coarser -c 4,8,2

.. figure:: figs/spe10_model2_coarser.png