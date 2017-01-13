#!/bin/bash -x

CC=mpicc
CXX=mpic++
export CC
export CXX

# if you want to slow the build down with some testing:
#HDF5TestExpress=3
#export HDF5TestExpress

if [ -z "$PREFIX" ]; then
    echo "PREFIX is not defined."
    exit 1
fi

if [ -z "$CPU_COUNT" ]; then
    echo "CPU_COUNT not set, setting to 2"
    CPU_COUNT=2
fi

echo "######## env ## and compilers ######"

env
which $CC
which $CXX

echo "#########################"

./configure --prefix=$PREFIX \
    --disable-production \
    --enable-debug \
    --enable-trace \
    --with-szlib=$PREFIX \
    --enable-threadsafe \
    --enable-unsupported \
    --enable-cxx \
    --with-default-api-version=v18 \
    --enable-parallel 

make -j$CPU_COUNT
make install


