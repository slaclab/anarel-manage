#!/usr/bin/bash -x

cd /reg/g/psdm/sw/conda/develop/rhel5
rm -rf valgrind-3.11.0
tar xfvj /reg/g/psdm/sw/conda/downloads/otherpkgs/valgrind-3.11.0.tar.bz2
cd valgrind-3.11.0
./configure prefix=/reg/g/psdm/sw/conda/inst/external/valgrind/valgrind-3.11.0/rhel5
make
make install
