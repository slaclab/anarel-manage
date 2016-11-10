#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

cd ..
pwd
ls
ls $PREFIX
if [ ! -d "$PREFIX/include" ]; then
    mkdir $PREFIX/include
fi
if [ ! -d "$PREFIX/lib" ]; then
    mkdir $PREFIX/lib
fi
cp -r cuda $PREFIX/cuda


