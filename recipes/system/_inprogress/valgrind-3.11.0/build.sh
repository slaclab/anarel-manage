#!/bin/bash -x

echo "######## env ############"
echo $REDHATVER
echo "#########################"

if [ -z ${REDHATVER} ]; then
echo "REDHATVER not set"
exit 1
fi

