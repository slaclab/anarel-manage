from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import re
import shlex
import subprocess
from  anarelmanage.util import run_command

def getLatestTagGit(tagurl):
    cmd = 'git ls-remote --tags %s' %tagurl
    output = subprocess.check_output(shlex.split(cmd))#, encoding='utf-8')
    # check stderr
    tags = [l.decode('ascii').split('\t')[1] for l in output.splitlines()]
    r = re.compile('.*?/(V\d\d-\d\d-\d\d)')
    prod_tags = []
    for tag in tags:
        match = re.search(r, tag)
        if match:
            prod_tags.append(match.group(1))
    prod_tags.sort()
    if len(prod_tags) == 0:
        print('Could not find any production tag')
        print(tagurl)
        return None
    return prod_tags[-1]

def getLatestTagSvn(tagurl):
    PRODUCTION_TAG = re.compile('^V\d\d-\d\d-\d\d')
    cmd = 'svn ls %s' % tagurl
    stdout, stderr = run_command(cmd, quiet=True)
    assert stderr=='', "stderr from cmd=%s\n%s" % (cmd, stderr)
    tags = []
    for tag in stdout.split('\n'):
        if PRODUCTION_TAG.match(tag):
            tags.append(tag)
    tags.sort()
    if len(tags)==0: return None
    return tags[-1]

def updateWithLatestTags(anaTags):
    repodict = {'psdm':"https://github.com/lcls-psana",
                'pcds':"file:///afs/slac/g/pcds/svn",
                'user':"https://pswww.slac.stanford.edu/svn/userrepo"}

    print("querying svn repos for latest tags of %d packages" % len(anaTags))
    print("make sure this account has access to repos (kinit username where username has read access)")
    sys.stdout.flush()
    for pkg, pkgdict in anaTags.items():
        repo = pkgdict['repo']
        assert repo in repodict.keys(), "pkg=%s, don't understand repo=%s" % (pkg, repo)
        if repo == 'psdm':
            tagsurl = repodict[repo] + '/' + pkg
            tag = getLatestTagGit(tagsurl)
        else:
            tagsurl = repodict[repo] + '/' + pkg + '/tags'
            tag = getLatestTagSvn(tagsurl)
        if tag.endswith('/'):
            tag = tag[0:-1]
        assert tag is not None, "pkg=%s url=%s got None" % (pkg, tagsurl)
        anaTags[pkg]['tag']=tag
        print("pkg=%s latest tag=%s" % (pkg,tag))
        sys.stdout.flush()


def checkoutCode(anaTags, master):
    repodict = {'psdm':"https://github.com/lcls-psana",
                'pcds':"file:///afs/slac/g/pcds/svn",
                'user':"https://pswww.slac.stanford.edu/svn/userrepo"}

    print("cheking out %d packages from ana tags list" % len(anaTags))
    sys.stdout.flush()

    for pkg, pkgdict in anaTags.items():
        repo = pkgdict['repo']
        assert repo in repodict.keys(), "pkg=%s, don't understand repo=%s" % (pkg, repo)
        assert 'tag' in pkgdict, "no tag defined for pkg=%s, not branches/conda" % pkg
        dest = pkg
        if pkgdict['subdir']:
            dest = '%s/%s' % (pkgdict['subdir'], pkg)
        # get repos from github
        if repo == 'psdm':
            pkgurl = repodict[repo] + '/' + pkg
            if master:
                cmd = 'git clone %s %s' %(pkgurl, dest)
            else:
                cmd = 'git clone --branch %s --depth 1 %s %s' %(pkgdict['tag'], pkgurl, dest)
        # get repos from svn
        else:
            pkgurl = repodict[repo] + '/' + pkg
            pkgurl += '/tags/%s' % pkgdict['tag']
            cmd = 'svn co %s %s' %(pkgurl, dest)
        print("----- %s ----" % cmd)
        sys.stdout.flush()
        stdout, stderr=run_command(cmd)
        if repo != 'psdm':
            assert stderr=='', "error with cmd: %s\n  stderr=%s" % (cmd, stderr)
        print(stdout)
        sys.stdout.flush()
    #sys.exit(0)

def readAnaTags(anaTagsFilename):
    assert os.path.exists(anaTagsFilename), "ana-tags file: %s doesn't exist" % anaTagsFilename
    tags = {}
    #for ii,ln in enumerate(file(anaTagsFilename).read().split('\n')):  # py2 -> py3
    for ii,ln in enumerate(open(anaTagsFilename, 'r').readlines()):
        ln = ln.strip()
        if len(ln)==0: continue
        if ln[0] == '#': continue
        flds = ln.split()
        assert len(flds)==4, "each line must read pkg svn=xx subdir=xx conda_branch=xx. But line %d is: %s" % (ii,ln)
        pkg = flds.pop(0)
        assert pkg not in tags, "line=%d redeclares package=%s, ln=%s" % (ii, pkg, ln)

        assert flds[0].startswith('svn='), "each line must read pkg svn=xx subdir=xx conda_branch=xx. But line %d is: %s" % (ii,ln)
        repo = flds[0].split('svn=')[1]

        assert flds[0].startswith('svn='), "each line must read pkg svn=xx subdir=xx conda_branch=xx. But line %d is: %s" % (ii,ln)
        repo = flds.pop(0).split('svn=')[1]

        assert flds[0].startswith('subdir='), "each line must read pkg svn=xx subdir=xx conda_branch=xx. But line %d is: %s" % (ii,ln)
        subdir = flds.pop(0).split('subdir=')[1]
        if subdir.lower()=='no':
            subdir = None

        assert flds[0].startswith('conda_branch='), "each line must read pkg svn=xx subdir=xx conda_branch=xx. But line %d is: %s" % (ii,ln)
        conda_branch = flds.pop(0).split('conda_branch=')[1]
        assert conda_branch.lower() in ['no', 'yes'], "conda_branch must be no or yes, ln %d = %s" % (ii, ln)
        if conda_branch.lower()=='no':
            conda_branch = False
        elif conda_branch.lower()=='yes':
            conda_branch = True
        tags[pkg] = {'repo':repo, 'subdir':subdir, 'conda_branch':conda_branch}

    return tags

def writeTagsFile(anaTags, filename):
    pkgs = sorted(anaTags.keys())
    #pkgs.sort()
    fout = open(filename, 'w')
    for pkg in pkgs:
        ln =  pkg.ljust(35)
        pkgdict = anaTags[pkg]
        keys = pkgdict.keys()
        for ky in sorted(keys):
            ln += ' '
            ln += ('%s=%s' % (ky.rjust(15), str(pkgdict[ky]).ljust(15)))
        fout.write('%s\n' % ln)
    fout.close()
