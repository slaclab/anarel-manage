#!/bin/bash -x

echo "######## env ## and compilers ######"
env
which gcc
which g++
echo "#########################"

./configure --prefix=$PREFIX --enable-shared

make SUBDIRS="src test" -j

make SUBDIRS="src test" install

