# needed to avoid file locking crash in mpi splitscan tests
export HDF5_USE_FILE_LOCKING=FALSE
export SIT_ROOT=/cds/sw/ds/ana/
export SIT_ARCH=x86_64-rhel7-gcc48-opt
eval "$(/cds/sw/ds/ana/conda1/inst/bin/conda shell.bash hook)"
conda activate ana-4.0.5$@
