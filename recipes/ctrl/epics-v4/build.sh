#!/bin/bash
install -d $PREFIX/bin
install -d $PREFIX/lib
install -d $PREFIX/epics-v4

# Install copy of the perl tool so the comment makes sense
# See makefile patch
cp -R tools $PREFIX/epics-v4
make config

# Build exampleCPP in place to package the example code too.
# (Also because we don't want to double the patch file count)
# Copy these folders over to the install directory.
cp -R exampleCPP $PREFIX/epics-v4

# Installs to PREFIX/epics-v4 instead of the build top
# See config_site patches
make -j$(getconf _NPROCESSORS_ONLN)

# Make examples in $PREFIX to avoid wayward hard-coded work directories
cd $PREFIX/epics-v4/exampleCPP
make

# Copy libraries into $PREFIX/lib
PKGS="pvCommonCPP pvDataCPP pvAccessCPP normativeTypesCPP pvaClientCPP pvDatabaseCPP pvaSrv"
for pkg in $PKGS ; do
  cp -av $PREFIX/epics-v4/$pkg/lib/$EPICS_HOST_ARCH/lib*so* $PREFIX/lib 2>/dev/null || : # linux
  cp -av $PREFIX/epics-v4/$pkg/lib/$EPICS_HOST_ARCH/lib*dylib* $PREFIX/lib 2>/dev/null || :  # osx
done

# Setup symlinks for utilities
BINS="eget pvget pvinfo pvlist pvput"
for file in $BINS ; do
  ln -s $PREFIX/epics-v4/pvAccessCPP/bin/$EPICS_HOST_ARCH/$file $PREFIX/bin
done

# deal with env export
mkdir -p $PREFIX/etc/conda/activate.d
mkdir -p $PREFIX/etc/conda/deactivate.d

ACTIVATE=$PREFIX/etc/conda/activate.d/epics_v4.sh
DEACTIVATE=$PREFIX/etc/conda/deactivate.d/epics_v4.sh

# set up
echo "export EPICS4_DIR=$PREFIX/epics-v4" >> $ACTIVATE

# tear down
echo "unset EPICS4_DIR" >> $DEACTIVATE

# make sure activate and deactivate scripts have exec permissions
chmod a+x $ACTIVATE
chmod a+x $DEACTIVATE

# clean up after self
unset ACTIVATE
unset DEACTIVATE
