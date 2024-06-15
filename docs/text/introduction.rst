============
Introduction
============

.. image:: ./figs/pycopm.gif

This documentation describes the content of the **pycopm** package.
The numerical studies are performed using the `Flow <https://opm-project.org/?page_id=19>`_ simulator. 

Concept
-------
Simplified and flexible framework for coarsening geological models. The initial implementation
included two available models in `opm-tests <https://github.com/OPM/opm-tests>`_: `norne <https://github.com/OPM/opm-tests/tree/master/norne>`_ 
and `drogon <https://github.com/OPM/opm-tests/tree/master/drogon>`_, where the coarser models are used to perform history matching studies using
the Ensemble based reservoir tool `ERT <https://ert.readthedocs.io/en/latest/>`_, via a :doc:`configuration file <./configuration_file>`. The current
available options for parameters to HM are the saturation functions using the LET model and permeabilities. The plan is to extend the functionality to
set up history matching/optimization studies using either `ERT <https://ert.readthedocs.io/en/latest/>`_, `PET <https://python-ensemble-toolbox.github.io/PET/>`_, 
or `everest <https://github.com/equinor/everest>`_.

In addition, current work focuces on creating coarser grids by only giving the input files
(i.e., avoiding the manual work to create templates as done for drogon and norne); see the :doc:`examples <./examples>`.

Overview
--------
The current implementation supports the following executable with the argument options:

.. code-block:: bash

    pycopm -i some_input -o some_output_folder

where 

- \-i, \-input: The base name of the :doc:`configuration file <./configuration_file>` or the name of the deck (`input.txt` by default).
- \-o, \-output: The base name of the :doc:`output folder <./output_folder>` (`output` by default).
- \-f, \-flow: Path to OPM Flow (`flow` by default).
- \-c, \-coarsening: Level of coarsening in the x, y, and z dir (`2,2,2` by default)

Installation
------------
See the `Github page <https://github.com/cssr-tools/pycopm>`_.

.. tip::
    Check the `CI.yml <https://github.com/cssr-tools/pycopm/blob/main/.github/workflows/CI.yml>`_ file.
