#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

# should be in cuda dir
pwd
ls

mkdir --parents $PREFIX/include
mkdir --parents $PREFIX/lib

cp include/cudnn.h $PREFIX/include/cudnn.h
cp lib64/lib* $PREFIX/lib/


