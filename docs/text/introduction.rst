============
Introduction
============

.. image:: ./figs/pycopm.gif

This documentation describes the content of the **pycopm** package.

Concept
-------
Simplified and flexible framework to create coarser OPM Flow geological models.

Roadmap
-------
In the initial development of the framework, the focus was two available models in `opm-tests <https://github.com/OPM/opm-tests>`_: `norne <https://github.com/OPM/opm-tests/tree/master/norne>`_ 
and `drogon <https://github.com/OPM/opm-tests/tree/master/drogon>`_, where the coarser models are used to perform history matching studies using
the Ensemble based reservoir tool `ERT <https://ert.readthedocs.io/en/latest/>`_, via a :doc:`configuration file <./configuration_file>`.

The current development of **pycopm** focuses on only creating coarser models (i.e., all needed input files to run OPM Flow) by only giving the OPM Flow input files
(i.e., avoiding the manual work to create templates as it was done for drogon and norne). This allows for flexibility to adapt the generated coarser decks in your
favourite history matching/optimization tool (e.g., `ERT <https://ert.readthedocs.io/en/latest/>`_, `PET <https://python-ensemble-toolbox.github.io/PET/>`_, `everest <https://github.com/equinor/everest>`_).

.. _overview:

Overview
--------
The current implementation supports the following executable with the argument options:

.. code-block:: bash

    pycopm -i some_input -o some_output_folder

where 

- \-i: The base name of the :doc:`configuration file <./configuration_file>` or the name of the deck (`input.txt` by default).
- \-o: The base name of the :doc:`output folder <./output_folder>` (`output` by default).
- \-f: OPM Flow full path to executable or just `flow` (`flow` by default).
- \-c: Level of coarsening in the x, y, and z dir (`2,2,2` by default).
- \-a: Use min, max, or mode to scale the actnum (`min` by default).
- \-j: Tunning parameter to avoid creation of nnc on the structural faults (`2.` by default).
- \-x: Vector of x-coarsening (`` by default).
- \-y: Vector of y-coarsening (`` by default).
- \-z: Vector of z-coarsening (`` by default).
- \-e: Use `utf8` or `ISO-8859-1` encoding to read the deck (`ISO-8859-1` by default).

Installation
------------
See the `Github page <https://github.com/cssr-tools/pycopm>`_.

.. tip::
    Check the `CI.yml <https://github.com/cssr-tools/pycopm/blob/main/.github/workflows/CI.yml>`_ file.

Getting started
---------------
See the :doc:`examples <./examples>`.

.. tip::
    Check the `tests <https://github.com/cssr-tools/pycopm/blob/main/tests>`_.
