# needed to avoid file locking crash in mpi splitscan tests
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ROOT=/cds/sw/ds/ana/
export SIT_ARCH=x86_64-rhel7-gcc48-opt
# needed for SRCF
export OPENBLAS_NUM_THREADS=1
eval "$(/cds/sw/ds/ana/conda1/inst/bin/conda shell.bash hook)"
ext=""
for arg in "$@"
do
  if [ "$arg" == "-py3" ]
  then
     ext="-py3"
  fi
done
conda activate ana-4.0.34$ext
