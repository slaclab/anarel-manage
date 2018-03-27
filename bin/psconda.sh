ana_current=$(head -n 1 /reg/g/psdm/sw/conda/current/ana/ana-current)
rhel_version=$(less /etc/redhat-release | grep -o -E '[0-9]+' | head -1)
export PATH=/reg/g/psdm/sw/conda/manage/bin:$PATH
. /reg/g/psdm/sw/conda/inst/miniconda2-prod-rhel$rhel_version/etc/profile.d/conda.sh
conda activate $ana_current
