=================
pycopm Python API
=================

The main script for the **pycopm** executable is located in the core folder. The different 
jobs called by ERT are located in the jobs folder. The reference_simulation folder contains
the generated files after running Flow in the Norne and drogon case in the opm-test folder. 
The template_scripts folder contains mako files based from the original decks in `opm-tests <https://github.com/OPM/opm-tests>`_. 
Finally, the utils folder contains different Python functions used in the framework for the coarsening.

.. figure:: figs/contents.png

   Files in the pyocpm package.

.. include:: modules.rst