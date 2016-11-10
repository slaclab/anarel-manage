#!/bin/bash -x

echo "----------------------------------------------------"
echo "--- starting build for openmpi, printing env -------"
env
echo "--- done printing env -------------------------------"

./configure \
    --prefix=$PREFIX \
    --with-lsf=/afs/slac/package/lsf/curr/ \
    --with-lsf-libdir=/afs/slac/package/lsf/curr/lib/ \
    --with-verbs

make -j $CPU_COUNT
make install

