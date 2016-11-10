#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

# build
CWD=$(pwd)
echo "Current dir: $CWD"
cd ..
mv $PKG_NAME-$PKG_VERSION $PKG_NAME
INCLUDEDIR=$PREFIX/include
TARGET=x86_$ARCH-rhel7-opt
make -C $PKG_NAME CFLAGS=-I$INCLUDEDIR $TARGET

# install
make -C $PKG_NAME INSTALLDIR=$PREFIX install quiet=

# install put libs in $PREFIX/lib but includes in
# $PREFIX/$PKG_NAME, we like that to go to $PREFIX/install/$PKG_NAME
mv $PREFIX/$PKG_NAME $PREFIX/include
