#!/bin/bash
source /reg/g/psdm/etc/psconda.sh
source activate ana-1.3.28-py3
cd $WORKSPACE
rm -rf build
mkdir build
cd build
cmake ..
make
make test
