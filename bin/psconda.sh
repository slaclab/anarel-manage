# needed to avoid file locking crash in mpi splitscan tests
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ROOT=/sdf/group/lcls/ds/ana/
export SIT_ARCH=x86_64-rhel7-gcc48-opt
export SIT_PSDM_DATA=/sdf/data/lcls/ds/
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
eval "$(/sdf/group/lcls/ds/ana/sw/conda1/inst/bin/conda shell.bash hook)"
if [ $py2 -eq 1 ]
then 
  export SIT_DATA=/sdf/group/lcls/ds/ana/sw/conda1/inst/envs/ana-4.0.45/data:/sdf/group/lcls/ds/ana/data/
  conda activate ana-4.0.45
else
  export SIT_DATA=/sdf/group/lcls/ds/ana/sw/conda1/inst/envs/ana-4.0.54-py3/data:/sdf/group/lcls/ds/ana/data/
  conda activate ana-4.0.54-py3
fi

#export SLURM_PRIORITY_RESERVATION=lcls:xppc00121_25
export SLURM_PRIORITY_RESERVATION=lcls:onshift
