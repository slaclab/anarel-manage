# Expects all checked out repos to be in ../repos
# If the 'py3' branch does not exist, the repo is skipped

import pathlib
import subprocess

p = pathlib.Path("../repos")
repos = p.glob("*")

for repo in repos:
    exitcode = subprocess.run('git checkout py3', cwd='../repos/{}'.format(repo), shell=True)
    if exitcode.returncode != 0:
       print('No py3 branch in {}'.format(repo))
       continue
    exitcode = subprocess.run('git merge master', cwd='../repos/{}'.format(repo), shell=True)
    if exitcode.returncode != 0:
       raise RuntimeError('Merge manually {}'.format(repo))
