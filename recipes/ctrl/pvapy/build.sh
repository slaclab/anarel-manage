#!/bin/bash
# Ignore the rest of the EPICS-CPP source and use installed v4
cd pvaPy

# Manual config because autoconf is broken for python 3
# I can be reasonably sure of the config here because of how conda works
RELEASE="configure/RELEASE.local"
echo "PVACLIENT = $EPICS4_DIR/pvaClientCPP" >> $RELEASE
echo "PVACCESS = $EPICS4_DIR/pvAccessCPP" >> $RELEASE
echo "NORMATIVETYPES = $EPICS4_DIR/normativeTypesCPP" >> $RELEASE
echo "PVDATA = $EPICS4_DIR/pvDataCPP" >> $RELEASE
echo "EPICS_BASE = $EPICS_BASE" >> $RELEASE

SITE="configure/CONFIG_SITE.local"
PYINC=`python -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())"`
echo "PVA_PY_CPPFLAGS = -I$PREFIX/include -I$PYINC" >> $SITE
if [ $PY3K == "1" ]; then
  #echo "PVA_PY_LDFLAGS = -L/usr/lib64 -L$PREFIX/lib -lboost_python3 -lboost_numpy -l$(basename $PYINC)" >> $SITE
  echo "PVA_PY_LDFLAGS = -L/usr/lib64 -L$PREFIX/lib -lboost_python3 -l$(basename $PYINC)" >> $SITE
else
  #echo "PVA_PY_LDFLAGS = -L/usr/lib64 -L$PREFIX/lib -lboost_python -lboost_numpy -l$(basename $PYINC)" >> $SITE
  echo "PVA_PY_LDFLAGS = -L/usr/lib64 -L$PREFIX/lib -lboost_python -l$(basename $PYINC)" >> $SITE
fi
echo "PVA_API_VERSION = 450" >> $SITE
echo "PVA_RPC_API_VERSION = 440" >> $SITE
#echo "HAVE_BOOST_NUM_PY = 1" >> $SITE
echo "HAVE_BOOST_NUM_PY = 0" >> $SITE
make

# Drop compiled pvaccess.so file into site-packages
cp lib/python/$EPICS_HOST_ARCH/pvaccess.so $PREFIX/lib/python$PY_VER/site-packages
