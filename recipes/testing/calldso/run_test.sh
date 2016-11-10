#!/bin/bash -x

echo "---- calldso/run_test.sh. pwd: ---"
pwd
echo "---- printing env: -------"
env
echo " --- done printing env ----"

chrpath $PREFIX/bin/calldso
$PREFIX/bin/calldso
cat $PREFIX/doc/calldso.txt
