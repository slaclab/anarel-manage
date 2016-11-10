#!/bin/bash -x

echo "######## env ## and compilers, and valgrind ######"
which gcc
which g++
which valgrind
echo "#########################"

if [ -z $REDHATVER ]; then
echo "REDHATVER not defined"
exit 1
fi

VALGRIND_PREFIX=/reg/g/psdm/sw/conda/inst/external/valgrind/valgrind-3.11.0/rhel$REDHATVER
echo VALGRIND_PREFIX
VALGRIND_EXECUTABLE=$VALGRIND_PREFIX/bin/valgrind
if [ ! -f $VALGRIND_EXECUTABLE ]; then
echo "path to valgrind not found"
exit 1
fi

if [ -z $PREFIX ]; then
echo "PREFIX not defined, setting to sandbox location"
PREFIX=/reg/g/psdm/sw/conda/sandbox/install/openmpi/openmpi-1.10.3/rhel7
fi

./configure --prefix=$PREFIX --with-lsf=/afs/slac/package/lsf/curr --with-lsf-libdir=/afs/slac/package/lsf/curr/lib --with-verbs --enable-debug --enable-memchecker --with-valgrind=$VALGRIND_PREFIX

make -j $CPU_COUNT
make install

