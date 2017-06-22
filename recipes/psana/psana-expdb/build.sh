#python update.py
#Currently the update.py command has to be run outside of the build.sh file in 
#order for the version number to actually be updated.

mkdir -p $PREFIX/lib

python dataPress.py
gcc -std=c99 -c -fpic updatedCFile.c
gcc -shared -o $PREFIX/lib/expnamedata.so updatedCFile.o 

pip install --no-deps --disable-pip-version-check .
