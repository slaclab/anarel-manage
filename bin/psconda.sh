# needed to avoid file locking crash in mpi splitscan tests
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ROOT=/reg/g/psdm
export SIT_ARCH=x86_64-rhel7-gcc48-opt
eval "$(/reg/g/psdm/sw/conda1/inst/miniconda2-prod-rhel7/bin/conda shell.bash hook)"
conda activate ana-2.0.13$@
