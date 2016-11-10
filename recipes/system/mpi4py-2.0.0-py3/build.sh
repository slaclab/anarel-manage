#!/bin/bash -x

echo "######## env ############"
env
echo "#########################"

python setup.py build
python setup.py install --prefix=$PREFIX

