#!/bin/bash
#
# Running this script builds either:
#    1) A psana environment
#              or 
#    2) If a version number is given, a complete
#       ana environment for both python 2 and 3
#
# It will exit for the following reasons:
# [(Release) means that it can only happen for offical builds
# and (Nightly) means it can only happen for the nightly builds
#   - It can't find the RHEL version number
#   - (Release) The build version number is invalid
#   - (Release) The build version number already exists
#   - (Nightly) The number of nightly tarballs does not equal
#     the number of envs (they should be equal)
#

#############################################################################
#---------------------------------VARIABLES---------------------------------#
#############################################################################
conda_setup="/reg/g/psdm/bin/conda_setup"
PREFIX="[JENKINS SCRIPT]:"
BUILDER=$(whoami)
HOSTNAME=$(hostname)
DATE=`date +%Y%m%d_hour%H`
MAX_BUILDS=5
echo "$PREFIX Building on ${HOSTNAME} as ${BUILDER}..."

# Find the RHEL number from the redhat-release text file
RHEL_VER=UNKNOWN
cat /etc/redhat-release | grep -q "release 7" && RHEL_VER=7
cat /etc/redhat-release | grep -q "release 6" && RHEL_VER=6
cat /etc/redhat-release | grep -q "release 5" && RHEL_VER=5
if [ $RHEL_VER = UNKNOWN ]; then
	echo "$PREFIX RHEL version could not be found. Aborting..."
	exit 1
fi

# Relevant directories
BASE_DIR="/reg/g/psdm/sw/conda/inst/miniconda2-prod-rhel${RHEL_VER}/envs"
CHANNEL_DIR="/reg/g/psdm/sw/conda/channels/psana-rhel${RHEL_VER}"

# Optionally accept a version number. Defaults to 99.99.99
VERSION=${1-"99.99.99"}
# Checks to make sure the version number is valid
# Of the form: d.d.d where d is 1 or more digits
if [[ ! $VERSION =~ [0-9]+\.[0-9]+\.[0-9]+ ]]; then
	echo "$PREFIX Invalid version number given: $VERSION"
	echo "$PREFIX Must be of form d.d.d where d is at least 1 digit..."
	echo "$PREFIX Aborting..."
	exit 1
fi
# Decides whether this is an  release or not
if [ $VERSION == "99.99.99" ]; then
	echo "$PREFIX Building nightly env..."
	RELEASE=false
	PREFIX="[JENKINS SCRIPT (NIGHTLY)]:"
else
	# If it is, make sure the version number doesn't already exist
	cd $BASE_DIR
	if [ ! -z $(ls | grep $VERSION) ]; then
		echo "$PREFIX Version $VERSION already exists for the psana build..."
		echo "$PREFIX Aborting..."
		exit 1
	fi
	echo "$PREFIX Building an official release of version $VERSION..."
	RELEASE=true
	PREFIX="[JENKINS SCRIPT (RELEASE)]:"
fi

# Temp directory for building and such
if [ $RELEASE = "false" ]; then
	CONDA_DIR="$BASE_DIR/conda-nightly"
else
	CONDA_DIR="$BASE_DIR/conda-release"
fi
##############################################################################
#------------------------------END OF VARIABLES------------------------------#
##############################################################################

# Exit with an exit code if there is an error
set -e

# Activate conda
source $conda_setup ""

# Remove old tmp directory and remake it
cd $BASE_DIR
if [ $RELEASE == "false" ]; then
	[ -d "conda-nightly" ] && rm -rf conda-nightly
	mkdir -p conda-nightly/downloads/anarel
else
	[ -d "conda-release" ] && rm -rf conda-release
	mkdir -p conda-release/downloads/anarel
fi

# Get the tags for the packages to be installed
cd $CONDA_DIR
echo "$PREFIX Retrieving tags..."
ana-rel-admin --force --cmd psana-conda-src --name $VERSION --basedir $CONDA_DIR
# Don't append "nightly" onto the tar file if it's a release...
# cause it's a release... not nightly
if [ $RELEASE == "false" ]; then
	mv downloads/anarel/psana-conda-${VERSION}.tar.gz downloads/anarel/psana-conda-nightly-${VERSION}.tar.gz
fi

# Get the recipe
echo "$PREFIX Retrieving recipe..."
cp -r /reg/g/psdm/sw/conda/manage/recipes/psana/psana-conda-opt .

# Make some changes to the yaml files
echo "$PREFIX Editing meta.yaml..."
# Get the yaml files for creating the envs
cp "/reg/g/psdm/sw/conda/manage/jenkins/ana-env-py2.yaml" .
cp "/reg/g/psdm/sw/conda/manage/jenkins/ana-env-py3.yaml" .
# Change names
if [ $RELEASE == "false" ]; then
	sed -i "s/{% set pkg =.*/{% set pkg = 'psana-conda-nightly' %}/" psana-conda-opt/meta.yaml
	sed -i "/^name:/ s/$/-nightly-${DATE}-py2/" ana-env-py2.yaml
	sed -i "/^name:/ s/$/-nightly-${DATE}-py3/" ana-env-py3.yaml
else
	sed -i "/^name:/ s/$/-${VERSION}/" ana-env-py2.yaml
	sed -i "/^name:/ s/$/-${VERSION}-py3/" ana-env-py3.yaml
fi
# These 3 packages are only on RHEL7, so remove them if this build isn't RHEL7
if [ ! $RHEL_VER == 7 ]; then
	sed -i "/yaml-cpp\|tensorflow\|jupyterhub/d" ana-env-py2.yaml
	sed -i "/yaml-cpp\|tensorflow\|jupyterhub/d" ana-env-py3.yaml
fi
# Change version and source directory to what it should be
sed -i "s/{% set version =.*/{% set version = '$VERSION' %}/" psana-conda-opt/meta.yaml
sed -i "/source:/!b;n;c \ \ fn: $CONDA_DIR/downloads/anarel/{{ pkg }}-{{ version }}.tar.gz" psana-conda-opt/meta.yaml

# Now build it
echo "$PREFIX Building tarball into $CHANNEL_DIR..."
conda-build --output-folder $CHANNEL_DIR psana-conda-opt

# It builds the tarball into $CHANNEL_DIR, now lets make the environment(s)
cd $CHANNEL_DIR/linux-64
if [ $RELEASE == "false" ]; then
	# Rename tarball cause nightly... duh.
	TAR=$(ls psana-conda-nightly-${VERSION}*)
	echo "$PREFIX Changing name from $TAR to psana-conda-nightly-${DATE}..."
	mv $TAR psana-conda-nightly-${DATE}.tar.bz2
	# Update the json file
	conda index
	# Create the environments based on the yaml files
	echo "$PREFIX Creating env for ${CHANNEL_DIR}/${TAR} in ${BASE_DIR}/ana-nightly-${DATE}..."
	conda env create -q -f $CONDA_DIR/ana-env-py2.yaml
	conda env create -q -f $CONDA_DIR/ana-env-py3.yaml
else
	# Don't rename the tarball (also duh)
	TAR=$(ls psana-conda-${VERSION}*)
	# Create the environments based on the yaml files
	echo "$PREFIX Creating env for ${CHANNEL_DIR}/${TAR} in ${BASE_DIR}/ana-${VERSION}"
	conda env create -q -f $CONDA_DIR/ana-env-py2.yaml
	conda env create -q -f $CONDA_DIR/ana-env-py3.yaml
fi

# Remove things not needed
echo "$PREFIX Running conda build purge..."
conda build purge
cd $BASE_DIR
if [ $RELEASE == "false" ]; then
	rm -rf conda-nightly
else
	rm -rf conda-release
fi

# If nightly check env/tarball count to maintain circular buffer of $MAX_BUILDS
if [ $RELEASE == "false" ]; then
	cd $BASE_DIR
	NUM_ENVS_PY2=$(ls | grep ana-nightly | grep py2 | wc -l)
	NUM_ENVS_PY3=$(ls | grep ana-nightly | grep py3 | wc -l)
	NUM_ENVS=$((NUM_ENVS_PY2 + NUM_ENVS_PY3))
	if [ $NUM_ENVS_PY2 -ne $NUM_ENVS_PY3 ]; then
		echo "$PREFIX Number of nightly py2 builds ($NUM_ENVS_PY2) does not equal the number of nightly py3 builds ($NUM_ENVS_PY3)..."
		echo "$PREFIX They should be equal..."
		echo "$PREFIX Nothing will be deleted. Aborting..."
		exit 1
	fi

	cd $CHANNEL_DIR/linux-64
	NUM_TARS=$(ls | grep psana-conda-nightly | wc -l)

	# First lets make sure there are an equal number of tarballs
	# and environment since they should be isomorphic (yay math terms)
	if [ $NUM_TARS -ne $((NUM_ENVS / 2)) ]; then
		echo "$PREFIX There are $NUM_TARS tarballs and $((NUM_ENVS / 2)) py2/py3 envs..."
		echo "$PREFIX They should be equal..."
		echo "$PREFIX Nothing will be deleted. Aborting..."
		exit 1
	fi

	# If they are, determine which environment(s) to delete if there are any
	cd $BASE_DIR
	if [ $((NUM_ENVS / 2)) -gt $MAX_BUILDS ]; then
		NUM_ENVS_TO_REMOVE=$(($NUM_ENVS - $MAX_BUILDS * 2))
		ENVS_TO_REMOVE=$(ls -t | grep ana-nightly | tail -n $NUM_ENVS_TO_REMOVE)

		echo "$PREFIX Removing $NUM_ENVS_TO_REMOVE env(s):"
		echo $ENVS_TO_REMOVE
		for ENV in ${ENVS_TO_REMOVE[@]}; do
		    conda remove --name $ENV --all
		done
	else
		echo "$PREFIX There are less than or equal to $MAX_BUILDS envs..."
		echo "$PREFIX No envs to remove..."
	fi

	# And same with tarball
	cd $CHANNEL_DIR/linux-64
	if [ $NUM_TARS -gt $MAX_BUILDS ]; then
		NUM_TARS_TO_REMOVE=$(($NUM_TARS - $MAX_BUILDS))
		TARS_TO_REMOVE=$(ls -t | grep psana-conda-nightly | tail -n $NUM_TARS_TO_REMOVE)

		echo "$PREFIX Removing $NUM_TARS_TO_REMOVE tarball(s):"
		echo $TARS_TO_REMOVE
		rm -rf $TARS_TO_REMOVE
	else
		echo "$PREFIX There are less than or equal to $MAX_BUILDS tarballs..."
		echo "$PREFIX No tarballs to remove..."
	fi

	echo "$PREFIX Finished building for $HOSTNAME as $BUILDER..."
else
    anaconda upload -u lcls-rhel${RHEL_VER} $(ls $CHANNEL_DIR/linux-64 | grep $VERSION)
    echo "$PREFIX Finished building official ana release version $VERSION for $HOSTNAME as $BUILDER..."
fi
