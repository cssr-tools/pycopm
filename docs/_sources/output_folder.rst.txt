=============
Output folder
=============

The following screenshot shows the generated ERT configuration file and folders in the selected output folder after executing **pycopm**
in the .

.. figure:: figs/output.png

    (Left) example of generated files after executing **pycopm** and (right) some of the figures in the postprocessing folder.

The generate ert.ert file can be run directly calling ERT for further studies, and some useful plots and files
are generated in the postprocessing folder. The OPM simulation results can be visualized using `ResInsight <https://resinsight.org>`_ .
Then after running **pycopm**, one could modify the generated OPM coarser related files in the preprocessing folder to adapt to
further existing frameworks (e.g., `PET <https://python-ensemble-toolbox.github.io/PET/>`_, `everest <https://github.com/equinor/everest>`_).