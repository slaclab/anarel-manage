#!/bin/bash

#Change meta.yaml
python AutomatedExpUpload.py

#Commence Building Operation
conda build reg/g/psdm/sw/conda/manage/recipie/psana/psana-expdb

#Initializing Upload to Anaconda.org
anaconda upload Path/to/package/.tar.bz2
