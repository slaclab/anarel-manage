#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

if [ -n $ANA_REL_DIR ]; then
    die "must define ANA_REL_DIR to the full "
    "release directory from which to make the psana conda pacakge. "
    "you can't use a test release, this release must be built from "
    "scratch against conda and have all the packages. "

# build
CWD=$(pwd)
echo "Current dir: $CWD"
