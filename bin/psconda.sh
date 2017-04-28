ana_current=$(head -n 1 /reg/g/psdm/sw/conda/current/ana/ana-current)
rhel_version=$(less /etc/redhat-release | grep -o -E '[0-9]+' | head -1)
base="/reg/g/psdm/sw/conda/inst/miniconda2-prod-rhel$rhel_version/envs"
if [[ $PATH = "" ]]; then
  export PATH=$base/$ana_current/bin:/reg/g/psdm/sw/conda/manage/bin
else
  export PATH=$base/$ana_current/bin:/reg/g/psdm/sw/conda/manage/bin:$PATH
fi
export CONDA_PREFIX=$base/$ana_current
export CONDA_DEFAULT_ENV=$ana_current
source $base/$ana_current/etc/conda/activate.d/env_vars.sh
