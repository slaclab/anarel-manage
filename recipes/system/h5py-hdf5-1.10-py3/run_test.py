# test our installation of h5py

import sys
import os
import numpy as np
import h5py

fname = 'run_test_helloworld.h5'
f = h5py.File(fname,'w')
f['data'] = 'hello world!'
f['data2'] = np.zeros((3,5), np.int32)
del f
h5 = h5py.File(fname,'r')
assert h5['data'].value == 'hello world!'
assert h5['data2'].shape[0]==3
assert h5['data2'].shape[1]==5
assert np.sum(h5['data2'][:])==0

del h5
os.unlink(fname)

from mpi4py import MPI
sys.stdout.write("mpi version: %r\n" % (MPI.get_vendor(),))
