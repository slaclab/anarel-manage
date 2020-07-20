# Checks out all repos listed in py3pkgs
# The repos are put in the ../repos directory
# The ../repos directory must already exist

import subprocess

fh=open('../pylib/anarelmanage/py3pkgs.txt')
lines=fh.readlines()
fh.close

for line in lines:
    repo = line.split(':')[1].strip()
    print('git clone https://github.com/lcls-psana/{} ../repos/{}'.format(repo, repo))
    exitcode = subprocess.run('git clone https://github.com/lcls-psana/{} ../repos/{}'.format(repo, repo), shell=True)
    if exitcode.returncode != 0:
        raise RuntimeError('Check problem: {}'.format(repo))
