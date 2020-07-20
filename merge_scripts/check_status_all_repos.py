# Expects all checked out repos to be in ../repos
# Shout be launched with the -u option (stdout not buffered),
# in order to have the output of 'run' correctly interspersed
# with the output of the print functions.

import pathlib
import subprocess

p = pathlib.Path("../repos")
repos = p.glob("*")

for repo in repos:
    print("\n>>>>> Processing:", repo)
    exitcode = subprocess.run('git status', cwd='../repos/{}'.format(repo), shell=True)
    if exitcode.returncode != 0:
       print('Deal manually with {}'.format(repo))
