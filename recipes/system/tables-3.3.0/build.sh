#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

export BZIP2_DIR=$PREFIX
export HDF5_DIR=$PREFIX
export LZO_DIR=$PREFIX
export CC=h5pcc

$PYTHON setup.py install --single-version-externally-managed --record record.txt

