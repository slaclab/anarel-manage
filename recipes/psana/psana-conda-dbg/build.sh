#!/bin/bash -x

## create the SConstruct file
if [ ! -e SConstruct ]; then
    ln -s SConsTools/src/SConstruct.main SConstruct
fi

## setup needed environment variables, if not defined,
if [ -z "$SIT_ARCH" ]; then
    echo "SIT_ARCH was not defined"
    return
fi

export SIT_RELEASE=`cat .sit_release`

if [ -z "$SIT_ROOT" ]; then
    export SIT_ROOT=/reg/g/psdm
    echo "SIT_ROOT was not defined, set it to $SIT_ROOT"
fi


export SIT_USE_CONDA=1

if [ -z $PREFIX ]; then
    echo "WARNING: PREFIX is not defined, script is not being run from conda-build, setting PREFIX for development purposes"
    export PREFIX=$CONDA_PREFIX
fi

export CONDA_ENV_PATH=$PREFIX

if [ ! -e '.sit_conda_env' ]; then
    echo $CONDA_ENV_PATH > '.sit_conda_env'
    echo "created .sit_conda_env file with $CONDA_ENV_PATH"
fi

CURDIR=`pwd`
export SIT_DATA="$CURDIR/data:$SIT_ROOT/data"
echo "set SIT_DATA to $SIT_DATA"

# build
CWD=$(pwd)
echo "Current dir: $CWD"

export PYTHONPATH=$CWD/arch/$SIT_ARCH/python:$PYTHONPATH
export LD_LIBRARY_PATH=$CWD/arch/$SIT_ARCH/lib
# put ana release bin second in path
export PATH=$CWD/arch/$SIT_ARCH/bin:$PATH
export PATH=$CONDA_ENV_PATH/bin:$PATH

echo "######## env ############"
env
echo "#########################"

mkanarel='SConsTools/src/tools/anarelinfo.py'
if [ ! -e "$mkanarel" ]; then
   echo "Script to make anarel info not found: $mkanarel"
   return
fi

# first we run mkanarel to make the ana release information
# package as a new source level package. This will let
# scons find it and install it in arch, then the conda-install
# target will pick it up and put it in conda site-packages.
python $mkanarel 
scons 
scons test
scons conda-install
