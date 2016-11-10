#!/bin/bash -x

echo "run_test.sh running from $PWD"

TESTDIR=$SRC_DIR/test
INCLUDEDIR=$PREFIX/include
g++ -o ndarray-test -I$INCLUDEDIR $TESTDIR/ndarray-test.cpp
g++ -o ndarray-unit-test -I$INCLUDEDIR $TESTDIR/ndarray-unit-test.cpp
./ndarray-test
./ndarray-unit-test
echo "ndarray tests succeeded!"
