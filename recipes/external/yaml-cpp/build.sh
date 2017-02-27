#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

# reset to master branch as of Feb 22, 2017, 738 commits to master,
# whereas 681 to 0.5.3 branch that still uses boost
git reset --hard bedb28fdb4fd52d97e02f6cb946cae631037089e

mkdir build
cd build
cmake -DBUILD_SHARED_LIBS=ON ..
make

cp -P libyaml-cpp* $PREFIX/lib/
cp -r ../include/yaml-cpp $PREFIX/include
