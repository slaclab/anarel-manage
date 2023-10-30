# needed to avoid file locking crash in mpi splitscan tests
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ROOT=/cds/group/psdm
export SIT_PSDM_DATA=/cds/data/psdm
export SIT_ARCH=x86_64-rhel7-gcc48-opt
# needed for SRCF
export OPENBLAS_NUM_THREADS=1
py2=0
v2=1
for arg in "$@"
do
  if [ "$arg" == "-py2" ]
  then
     py2=1
  fi
  if [ "$arg" == "-v1" ]
  then
     v2=0
  fi
done
if [ $v2 -eq 1 ]
then
  eval "$(/cds/sw/ds/ana/conda1-v2/inst/bin/conda shell.bash hook)"
  export CONDA_ENVS_DIRS=/cds/sw/ds/ana/conda1/inst/envs/
else
  eval "$(/cds/sw/ds/ana/conda1/inst/bin/conda shell.bash hook)"
fi
if [ $py2 -eq 1 ]
then 
  export SIT_DATA=/cds/sw/ds/ana/conda1/inst/envs/ana-4.0.45/data:/cds/group/psdm/data/
  conda activate ana-4.0.45
else
  export SIT_DATA=/cds/sw/ds/ana/conda1/inst/envs/ana-4.0.54-py3/data:/cds/group/psdm/data/
  conda activate ana-4.0.54-py3
fi
