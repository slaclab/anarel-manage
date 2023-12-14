# needed to avoid file locking crash in mpi splitscan tests
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ARCH=x86_64-rhel7-gcc48-opt

if [ -d "/sdf/group/lcls/" ]
then
    # s3df
    export SIT_ROOT=/sdf/group/lcls/ds/ana
    export SIT_PSDM_DATA=/sdf/data/lcls/ds
    eval "$(/sdf/group/lcls/ds/ana/sw/conda1-v3/inst/bin/conda shell.bash hook)"
    export CONDA_ENVS_DIRS=/sdf/group/lcls/ds/ana/sw/conda1/inst/envs
else
    # psana
    export SIT_ROOT=/cds/group/psdm
    export SIT_PSDM_DATA=/cds/data/psdm
    eval "$(/cds/sw/ds/ana/conda1-v2/inst/bin/conda shell.bash hook)"
    export CONDA_ENVS_DIRS=/cds/sw/ds/ana/conda1/inst/envs
fi

# needed for SRCF
export OPENBLAS_NUM_THREADS=1
py2=0
for arg in "$@"
do
  if [ "$arg" == "-py2" ]
  then
     py2=1
  fi
done

if [ $py2 -eq 1 ]
then 
  export SIT_DATA=$CONDA_ENVS_DIRS/ana-4.0.45/data:$SIT_ROOT/data/
  conda activate ana-4.0.45
else
  export SIT_DATA=$CONDA_ENVS_DIRS/ana-4.0.57-py3/data:$SIT_ROOT/data/
  conda activate ana-4.0.57-py3
fi
