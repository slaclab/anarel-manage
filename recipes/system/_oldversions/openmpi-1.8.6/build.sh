#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

./configure \
    --prefix=$PREFIX \
    --with-lsf=/afs/slac/package/lsf/curr/ \
    --with-lsf-libdir=/afs/slac/package/lsf/curr/lib/ \
    --with-verbs

make -j $CPU_COUNT
make install

