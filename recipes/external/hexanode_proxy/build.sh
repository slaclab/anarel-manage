#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

cd x86_64-centos7-gcc485

# this is weird to have the library filename different than the package name,
# I almost want to rename it to libhexanode64c_x64.a, but maybe the package author 
# should think about doing this?
mkdir -p $PREFIX/lib
mkdir -p $PREFIX/include/hexanode_proxy

cp libResort64c_x64.a $PREFIX/lib/
cp resort64c.h $PREFIX/include/hexanode_proxy/
