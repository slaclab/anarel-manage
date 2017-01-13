#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

export HDF5_DIR=$PREFIX
export CC=mpicc
python setup.py configure --mpi
$PYTHON setup.py build
$PYTHON setup.py install

