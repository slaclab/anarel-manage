# needed to avoid file locking crash in mpi splitscan tests
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ROOT=/cds/sw/ds/ana/
export SIT_ARCH=x86_64-rhel7-gcc48-opt
# needed for SRCF
export OPENBLAS_NUM_THREADS=1
ext=""
v2=0
for arg in "$@"
do
  if [ "$arg" == "-py3" ]
  then
     ext="-py3"
  fi
  if [ "$arg" == "-v2" ]
  then
     v2=1
  fi
done
if [ $v2 -eq 1 ]
then
  eval "$(/cds/sw/ds/ana/conda1-v2/inst/bin/conda shell.bash hook)"
  export CONDA_ENVS_DIRS=/cds/sw/ds/ana/conda1/inst/envs/
else
  eval "$(/cds/sw/ds/ana/conda1/inst/bin/conda shell.bash hook)"
fi
conda activate ana-4.0.44$ext
