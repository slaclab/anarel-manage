#!/bin/bash

# unset unused old fortran compiler vars
unset F90 F77

set -e

export FCFLAGS="$FFLAGS"

# avoid absolute-paths in compilers
export CC=$(basename "$CC")
export CXX=$(basename "$CXX")
export FC=$(basename "$FC")

if [ $(uname) == Darwin ]; then
    if [[ ! -z "$CONDA_BUILD_SYSROOT" ]]; then
        export CFLAGS="$CFLAGS -isysroot $CONDA_BUILD_SYSROOT"
        export CXXFLAGS="$CXXFLAGS -isysroot $CONDA_BUILD_SYSROOT"
    fi
    export LDFLAGS="$LDFLAGS -Wl,-rpath,$PREFIX/lib"
fi

export LIBRARY_PATH="$PREFIX/lib"

./configure --prefix=$PREFIX \
            --disable-dependency-tracking \
            --enable-mpi-fortran \
            --disable-wrapper-rpath \
            --disable-wrapper-runpath \
            --with-lsf=/afs/slac/package/lsf/curr/ \
            --with-lsf-libdir=/afs/slac/package/lsf/curr/lib/ \
            --with-wrapper-cflags="-I$PREFIX/include" \
            --with-wrapper-cxxflags="-I$PREFIX/include" \
            --with-wrapper-fcflags="-I$PREFIX/include" \
            --with-wrapper-ldflags="-L$PREFIX/lib -Wl,-rpath,$PREFIX/lib" \
            --with-sge \

make -j"${CPU_COUNT:-1}"
make install

if [ $(uname) == Darwin ]; then
    # workaround for open-mpi/ompi#7516
    echo "setting the mca gds to hash..."
    echo "gds = hash" >> $PREFIX/etc/pmix-mca-params.conf

    # workaround for open-mpi/ompi#5798
    echo "setting the mca btl_vader_backing_directory to /tmp..."
    echo "btl_vader_backing_directory = /tmp" >> $PREFIX/etc/openmpi-mca-params.conf
fi
