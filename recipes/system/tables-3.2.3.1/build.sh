#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

export HDF5_DIR=$PREFIX
export CC=h5pcc

echo hi
$PYTHON setup.py install --prefix=$PREFIX --hdf5=$PREFIX

