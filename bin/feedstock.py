# see https://confluence.slac.stanford.edu/display/PSDMInternal/Feedstock+Releases#FeedstockReleases-LCLS2

import sys
import os
import subprocess
import argparse

build_waves = [
[
'ndarray-psana-feedstock',
'ndarray-psana-py2-feedstock',
'stdcompat-feedstock',
'sz-feedstock',
'psgeom-feedstock',
'xtcav2-feedstock',
'xtcav2-py2-feedstock',
'psocake-feedstock',
'psocake-py2-feedstock',
],
[
'psana1-py2-feedstock',
'psana1-feedstock',
'libpressio-feedstock',
],
]

all_repos = []
for build_wave in build_waves: all_repos+=build_wave

def do_cmd(user_cmd,selected_repos):
    for mydir in selected_repos:
        assert os.path.isdir(mydir)
        cmd = 'cd '+mydir+'; '+user_cmd+'; cd ..'
        output = subprocess.run(cmd, shell=True, capture_output=True, encoding='utf-8')
        print(30*'-',mydir,'\n',output.stdout,output.stderr)

def inc_build_num_selected(mydir,setzero=False):
    fname = mydir+'/recipe/meta.yaml'
    with open(fname,'r') as f:
        lines = f.readlines()
        for nline,line in enumerate(lines):
            if 'number:' in line:
                if setzero:
                    newnumber = 0
                else:
                    newnumber = int(line.split()[1])+1
                newline = line[:line.index(':')+1]+' '+str(newnumber)+'\n'
                lines[nline]=newline
                break
    print('*** new build number:',newnumber)
    with open(fname,'w')as f:
        for line in lines:
            f.write('%s'%line)

def inc_build_num():
    for mydir in all_repos:
        assert os.path.isdir(mydir)
        response = input('Increment or zero build number for '+mydir+'? <y/N/0>:')
        if response=='y' or response=='Y':
            inc_build_num_selected(mydir)
        elif  response=='0':
            inc_build_num_selected(mydir,True)

def clone():
    git_prefix = 'git@github.com:slac-lcls/'
    for mydir in all_repos:
        cmd = 'git clone '+git_prefix+mydir
        output = subprocess.run(cmd, shell=True, capture_output=True, encoding='utf-8')
        print(30*'-',mydir,'\n',output.stdout,output.stderr)

parser = argparse.ArgumentParser()
parser.add_argument("--wave", type=int, help="only do command for specified build wave", default=None)
parser.add_argument("--clone", action='store_true', help="clone repos")
parser.add_argument("--incbuildnum", action='store_true', help="increment build numbers")
parser.add_argument("--cmd", help="command to perform in all directories")
args = parser.parse_args()

if args.wave is not None:
    selected_repos=build_waves[args.wave]
else:
    selected_repos=all_repos

if args.clone:
    clone()
elif args.incbuildnum:
    inc_build_num()
else:
    do_cmd(args.cmd,selected_repos)
