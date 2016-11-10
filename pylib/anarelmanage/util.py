from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import stat
import subprocess as sb
import platform
import math
import sys
import re
import json

# utility functions for ana-rel-admin

CONFIG='ANA_REL_ADMIN_CONFIG_DIR'
RECIPES='ANA_REL_ADMIN_RECIPE_DIR'

def _getTopSubDir(subdir):
    anarelmanagePath = os.path.abspath(os.path.split(__file__)[0])
    pylibPath = os.path.split(anarelmanagePath)[0]
    topPath = os.path.split(pylibPath)[0]
    subPath = os.path.join(topPath, subdir)
    assert os.path.exists(subPath), " %s doesn't exist" % subPath
    return subPath

def setConfigDir(configdir=None):
    global CONFIG    
    if os.environ.get(CONFIG,None) is not None:
        print("ana-rel-admin.setConfigDir: %s already set, not setting config dir to %s" % (CONFIG, configdir))
        return
    else:
        configdir = _getTopSubDir('config')
    os.environ[CONFIG] = configdir
    
def setRecipesDir(recipedir=None):
    global RECIPES
    if os.environ.get(RECIPES,None) is not None:
        print("ana-rel-admin.setRecipesDir: %s already set, not setting config dir to %s" % (RECIPES, recipedir))
        return
    else:
        configdir = _getTopSubDir('recipes')
    os.environ[RECIPES] = configdir
    
def getFile(location, fname):
    global CONFIG
    global RECIPES
    assert location in ['config', 'recipes']
    if location == 'config':
        basedir = os.environ[CONFIG]
    else:
        basedir = os.environ[RECIPES]
    assert os.path.exists(basedir), "location directory %s doesn't exist" % basedir
    fullpath = os.path.join(basedir, fname)
    assert os.path.exists(fullpath), "file: %s doesn't exist" % fullpath
    return fullpath

def whichCondaInstall(condaInstallBaseDir):
    '''takes a look at where os comes from, should be something like
     /reg/g/psdm/sw/conda/inst/miniconda2-dev-rhel7/envs/myenv/lib/os.py
    
    checks that this starts with the condaInstallBaseDir arg, then 
    checks that inst is the next subdir, then returns what follows, i.e, 
    returns miniconda2-dev-rhel7 for above
    '''
    pythonLib = os.path.split(os.__file__)[0]
    if not pythonLib.startswith(condaInstallBaseDir):
        warning("whichMiniCondaInstall called for non central install, basedir arg=%s but os imports from %s"  % (condaInstallBaseDir, pythonLib))
        return 'non-central-miniconda-install'
    relpath = pythonLib.split(condaInstallBaseDir)[1]
    dirs = relpath.split(os.path.sep)
    if dirs[0]=='': dirs.pop(0)
    assert dirs[0]=='inst', "unexpected - central install conda dir layout has changed. Expected 'inst' at start of %s" % relpath
    return dirs[1]

def getEnvRootDir(condaRootPath, envName):
    '''given a CONDA_PREFIX, will try to grow to env/envName and return if it all exists
    '''
    assert os.path.exists(condaRootPath), "path %s doesn't exist" % condaRootPath
    envBaseDir = os.path.join(condaRootPath, 'envs')
    assert os.path.exists(envBaseDir), "path %s doesn't exist" % envBaseDir
    envRoot = os.path.join(envBaseDir, envName)
    assert os.path.exists(envRoot), "path %s doesn't exist" % envRoot
    return envRoot

def logDir(basedir):
    _logDir = os.path.join(basedir, 'logs')    
    assert os.path.exists(_logDir), "log dir %s doesn't exist" % _logDir
    return _logDir

def run_command(cmd_or_cmdList, stderr_in_stdout=False, quiet=False, shell=True):
    '''run command. return both stdout and stderr, or just both (if stderr_in_stdout=True)
    '''
    if not quiet:
        print(cmd_or_cmdList)

    if stderr_in_stdout:
        p = sb.Popen(cmd_or_cmdList, shell=shell, stdout=sb.PIPE, stderr=sb.STDOUT)
        out = p.communicate()
        return out
    else:
        p = sb.Popen(cmd_or_cmdList, shell=shell, stdout=sb.PIPE, stderr=sb.PIPE)
        stdout, stderr = p.communicate()
        return stdout, stderr.strip()

def removeIfPresent(fname):
    if os.path.exists(fname):
        print("rm %s " % fname)
        os.unlink(fname)
    else:
        print("## file %s ## doesn't exist" % fname)

def warning(msg):
    sys.stderr.write("WARNING: %s\n" % msg)
    sys.stderr.flush()
    
def error(msg):
    sys.stderr.write("ERROR: %s\n" % msg)
    sys.stderr.flush()
    sys.exit(1)

def getOsAndPlatform():
    platform_string = platform.platform()
    if platform_string.startswith('Darwin'):
        return 'osx','osx'
    elif platform_string.startswith('Linux'):
        if '-redhat-' in platform_string:
            version_string = platform_string.split('-redhat-')[1].split('-')[0]
            major_version = int(math.floor(float(version_string)))
            archMachine = platform.machine()
            assert archMachine == 'x86_64', "unexpected - machine architechture is not x86_64"
            return 'rhel%d' % major_version, 'linux-64'
    raise Exception("could not determin Os/platform. Only looked for Darwin and redhat linux, but platform string is %s" % platform_string)

def dprint(verbose, msg):
    if verbose:
        print(msg)

def getSITvariables(verbose=False, debug=False):
    '''return dictionary of all SIT variables needed for build
    '''
    osName, platStr = getOsAndPlatform()
    dprint(verbose,"osName=%s" % osName)
    dprint(verbose,"platform=%s" % platform)
    compiler = os.environ.get('CC','gcc')
    stdout, stderr = run_command(['which', compiler], shell=False)
    assert stderr.strip()=='', "no compiler found. Tried %s" % compiler
    dprint(verbose,"compiler=%s" % compiler)
    stdout, stderr = run_command([compiler, '--version'], shell=False)
    assert stderr.strip()=='', "found compiler=%s, but command %s --version produced error:\n%s\nstdout=%s" % \
        (compiler, compiler, stderr, stdout)
    dprint(verbose, "%s --version produced:\nstdout=%s\nstderr=%s" % (compiler, stdout, stderr))
    COMPILER_VERSION = re.compile('\s+(\d+\.\d+)\.\d+')
    lineOneOfVersionOutput = stdout.split('\n')[0]
    ccVerMatch = re.search(COMPILER_VERSION, lineOneOfVersionOutput)
    assert ccVerMatch, "could not identify a complier version from first line of %s --version which is: %s" % (compiler, lineOneOfVersionOutput)
    versionWithDot = ccVerMatch.groups()[0]
    versionWithoutDot = ''.join(versionWithDot.split('.'))
    archMachine = platform.machine()
    optOrDebug = {False:'opt', True:'dbg'}[debug]
    sitVars = {'SIT_ARCH':'%s-%s-%s%s-%s' % (archMachine, osName, compiler, versionWithoutDot, optOrDebug)}
    sitVars['SIT_ROOT'] = '/reg/g/psdm'
    return sitVars
    
def strip_warnings_and_harmless_messages(txt):
    def ignore(ln):
        ln = ln.strip()
        if len(ln)==0: return True
        ln = ln.lower()
        if ln.find('warning')>=0: return True
        if ln.startswith('subprocess exiting'): return True
        # two characters, probably a number, can't be an error?
        if len(ln)<=2: return True
        sys.stderr.write("bad line: %s\n" % ln)
        return False

    lns = txt.split('\n')
    error_lines = [ln for ln in lns if not ignore(ln)]
    return '\n'.join(error_lines)

def condaEnvs():
    envnames = []
    cmd = 'conda env list --json'
    stdout, stderr = run_command(cmd)
    assert stderr.strip()==''
    envs = json.loads(stdout)
    assert 'envs' in envs, "key 'env' not in json output of %s, output=%s, json loads as=%r" % (cmd, stdout, envs)
    envs = envs['envs']
    if len(envs)==0:
        return None,[]
    envRoot = os.path.split(envs[0])[0]
    return envRoot, [os.path.split(env)[1] for env in envs]

def get_md5(path):
    cmd='md5sum "%s"' % path
    o,e = run_command(cmd, quiet=True)
    assert e.strip()=='', "stderr=%s cmd=%s" % (e,cmd)
    return o.split()[0]
        
def get_md5_listing(envRootDir, output_file):
    listing = []
    for root, dirs, files in os.walk(envRootDir):
        for fname in files:
            path = os.path.join(root, fname)
            md5 = get_md5(path)
            ext = os.path.splitext(fname)[1]
            listing.append((ext, path.split(envRootDir)[1], md5))
    listing.sort()
    longestPath = max([len(res[1]) for res in listing])
    fout = file(output_file,'w')
    for res in listing:
        fout.write("%s md5sum=%s\n" % (res[1].ljust(longestPath), res[2]))
    fout.close()
    return len(listing)

def checkPoint(basedir, relname, stage):
    condaInstall = whichCondaInstall(basedir)
    output_file = os.path.join(basedir, 'scratch', '-'.join([condaInstall, relname, stage]))
    output_file += '.checkpoint'
    envRootDir = getEnvRootDir(os.path.join(basedir, 'inst', condaInstall), relname)
    numFiles = get_md5_listing(envRootDir, output_file)
    return output_file, numFiles

def compareCheckPointFiles(filenameA, filenameB, return_string=False):
    linesA=file(filenameA,'r').read().split('\n')
    linesB=file(filenameB,'r').read().split('\n')

    def makeFname2md5(lines, fname):
        res = {}
        for idx, ln in enumerate(lines):
            ln = ln.strip()
            if len(ln)==0: continue
            if ln.startswith('#'): continue
            assert ln.find('md5sum=')>0, "line %d of file %s does not have md5sum= in it, ln=%s" % (idx, fname, ln)
            lnFlds = ln.split('md5sum=')
            md5sum = lnFlds.pop()
            fname = 'md5sum='.join(lnFlds)
            fname = fname.strip()
            res[fname]=md5sum
        return res

    A_fname2md5 = makeFname2md5(linesA, filenameA)
    B_fname2md5 = makeFname2md5(linesB, filenameB)

    msg = ''
    for fname, md5 in A_fname2md5.iteritems():
        if fname in B_fname2md5:
            md5B = B_fname2md5[fname]
            if md5 != md5B:
                msg += 'A file changed. md5old=%s md5new=%s fname=%s\n' % (md5, md5B,fname)
        else:
            msg += "A file not in B: %s\n" % fname
    if return_string:
        return msg
    print(msg)


def addToActivateDeactivateGPUVariables(envDir):
    actEnv = os.path.join(envDir, 'etc', 'conda', 'activate.d', 'env_vars.sh')
    deactEnv = os.path.join(envDir, 'etc', 'conda', 'deactivate.d', 'env_vars.sh')
    assert os.path.exists(actEnv), "trying to add GPU env vars but %s doesn't exist" % actEnv
    assert os.path.exists(deactEnv), "trying to add GPU env vars but %s doesn't exist" % deactEnv
    libdir = os.path.join(envDir,'lib')
    assert os.path.exists(libdir), "This environment doesn't have a libdir: %s" % libdir
    incdir = os.path.join(envDir,'include')
    assert os.path.exists(incdir), "This environment doesn't have a incdir: %s" % incdir

    foutAct = file(actEnv, 'a')
    foutDeact = file(deactEnv, 'a')

    to_modify=['LD_LIBRARY_PATH','CPATH','PATH']
    newvals=['/usr/local/cuda/lib64:%s'%libdir,
              incdir,
              '/usr/local/cuda/bin']
    for ky, newval in zip(to_modify, newvals):
        foutAct.write("export BEFORE_GPU_%s=$%s\n" % (ky, ky))
        foutAct.write("export %s=$%s:%s\n" % (ky, ky, newval))
        foutDeact.write("export %s=$BEFORE_GPU_%s\n" % (ky, ky))
        foutDeact.write("unset BEFORE_GPU_%s\n" % ky)
        foutDeact.write("export BEFORE_GPU_%s\n" % ky)
    foutAct.close()
    foutDeact.close()

def createSitVarsCondaEnv(dbg, force=False, envDir=None):
    sitVars = getSITvariables(debug=dbg)
    if envDir is None:
        envDir = os.environ.get('CONDA_PREFIX', None)
    assert envDir, "activate the environment you want to add setup to - currently CONDA_PREFIX is not set, it needs to be the full path to the environment"
    assert os.path.exists(envDir), "envdir=%s doesn't exist" % envDir
    os.chdir(envDir)
    if 'etc' not in os.listdir('.'):
        os.mkdir('etc')
    os.chdir('etc')
    if not force:
        ans = raw_input("Are you sure you want to create env_vars.sh files in the activate/deactivate scripts for the current environment=%s?" % envDir)
        if not (ans.lower().strip() in ['y','yes']):
            print("Answer was not y or yes, exiting")
            return
    if not 'conda' in os.listdir('.'):
        os.mkdir('conda')
    os.chdir('conda')
    if not 'activate.d' in os.listdir('.'):
        os.mkdir('activate.d')
    if not 'deactivate.d' in os.listdir('.'):
        os.mkdir('deactivate.d')
    os.chdir('activate.d')
    createFile = True
    if os.path.exists('env_vars.sh') and not force:
        print("The env_vars.sh file already exists in %s" % os.path.join(envDir, 'etc', 'conda', 'activate.d'))
        ans = raw_input("do you want to overwrite it? (y or yes)")
        createFile = ans.lower().strip() in ['y','yes']
    if createFile:
        fout = file('env_vars.sh','w')
        fout.write("#!/bin/sh\n")
        fout.write("export SIT_DATA=%s/data:/reg/g/psdm/data\n" % envDir)
        fout.write("export SIT_ARCH=%s\n" % sitVars['SIT_ARCH'])
        fout.write("export SIT_ROOT=%s\n" % sitVars['SIT_ROOT'])
        fout.close()
    else:
        print("did not overwrite file")
    os.chdir('..')
    os.chdir('deactivate.d')
    createFile = True
    if os.path.exists('env_vars.sh') and not force:
        print("The env_vars.sh file already exists in %s" % os.path.join(envDir, 'etc', 'conda', 'deactivate.d'))
        ans = raw_input("do you want to overwrite it? (y or yes)")
        createFile = ans.lower().strip() in ['y','yes']
    if createFile:
        fout = file('env_vars.sh','w')
        fout.write("#!/bin/sh\n")
        fout.write("unset SIT_DATA\n")
        fout.write("unset SIT_ARCH\n")
        fout.write("unset SIT_ROOT\n")
        fout.write("export SIT_DATA\n")
        fout.write("export SIT_ARCH\n")
        fout.write("export SIT_ROOT\n")
        fout.close()
    else:
        print("did not overwrite file")

def checkFixPermissionsForPath(pth):
    mode = os.stat(pth).st_mode
    groupReadable = stat.S_IRGRP & mode == stat.S_IRGRP
    otherReadable = stat.S_IROTH & mode == stat.S_IROTH
    msg = ''
    if not groupReadable:
        msg += ' not group readable'
        mode |= stat.S_IRGRP
    if not otherReadable:
        msg += ' not other readable'
        mode |= stat.S_IROTH
    if len(msg.strip())>0:
        print("%s, fixing permissions for %s" % (msg, pth))
        os.chmod(pth, mode)

def checkFixPermissions(envRoot):
    for root, dirs, files in os.walk(envRoot):
        for fname in dirs + files:
            pth = os.path.join(root,fname)
            checkFixPermissionsForPath(pth)
