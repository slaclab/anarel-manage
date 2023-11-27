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

CONFIG = None
RECIPES = None

def _getTopSubDir(subdir):
    anarelmanagePath = os.path.abspath(os.path.split(__file__)[0])
    pylibPath = os.path.split(anarelmanagePath)[0]
    topPath = os.path.split(pylibPath)[0]
    subPath = os.path.join(topPath, subdir)
    assert os.path.exists(subPath), " %s doesn't exist" % subPath
    return subPath

def getConfigDir():
    global CONFIG
    if CONFIG is None:
        CONFIG = _getTopSubDir('config')
    return CONFIG

def getRecipesDir():
    global RECIPES
    if RECIPES is None:
        RECIPES = _getTopSubDir('recipes')
    return RECIPES

def getPsanaTagsFile(tagsfile):
    if os.path.exists(tagsfile):
        return os.path.abspath(tagsfile)
    return getFile('config',tagsfile)

def getFile(location, fname):
    assert location in ['config', 'recipes']
    if location == 'config':
        basedir = getConfigDir()
    else:
        basedir = getRecipesDir()
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
        stdout, stderr = p.communicate()
        return stdout
    else:
        p = sb.Popen(cmd_or_cmdList, shell=shell, stdout=sb.PIPE, stderr=sb.PIPE)
        stdout, stderr = p.communicate()
        return stdout, stderr.strip()

def removeIfPresent(fname):
    if os.path.exists(fname):
        print("rm %s " % fname)
        os.unlink(fname)
        return True
    else:
        print("## file %s ## doesn't exist" % fname)
        return False

def warning(msg):
    sys.stderr.write("WARNING: %s\n" % msg)
    sys.stderr.flush()

def error(msg):
    sys.stderr.write("ERROR: %s\n" % msg)
    sys.stderr.flush()
    sys.exit(1)

def getOsAndPlatform():
    platform_string = platform.platform()  # Linux-3.10.0-1160.76.1.el7.x86_64-x86_64-with-glibc2.17
                                           # Linux-3.10.0-1160.76.1.el7.x86_64-x86_64-with-redhat-7.9-Maipo
    print('platform_string:', platform_string)

    if platform_string.startswith('Darwin'):
        return 'osx','osx'
    elif platform_string.startswith('Linux'):
        if '-redhat-' in platform_string:
            version_string = platform_string.split('-redhat-')[1].split('-')[0]
            major_version = int(math.floor(float(version_string[:2])))
            archMachine = platform.machine()  # x86_64
            assert archMachine == 'x86_64', "unexpected - machine architechture is not x86_64"
            return 'rhel%d' % major_version, 'linux-64'
        if '-glibc2.' in platform_string and '.el7.' in platform_string:
            archMachine = platform.machine()  # x86_64
            assert archMachine == 'x86_64', "unexpected - machine architechture is not x86_64"
            return 'rhel7', 'linux-64'

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

REGEXP_VERSION_STR = re.compile('(\d+)\.(\d+)\.(\d+)(\w*)')
def validVersionStr(version_str):
    match = re.match(REGEXP_VERSION_STR, version_str)
    return not (None is match)

def versionGreater(verNew, verCur):
    matchNew = re.match(REGEXP_VERSION_STR, verNew)
    matchCur = re.match(REGEXP_VERSION_STR, verCur)
    assert matchNew, "verNew=%s doesn't match %s"  % (verNew, REGEXP_VERSION_STR)
    assert matchCur, "verCur=%s doesn't match %s"  % (verCur, REGEXP_VERSION_STR)
    for gr in [1,2,3,4]:
        if int(matchNew.group(gr)) > int(matchCur.group(gr)): return True
        if int(matchNew.group(gr)) < int(matchCur.group(gr)): return False
    return False

def psanaCondaPackageName(version_str):
    assert validVersionStr(version_str), "psana conda package version string should be n.n.nxx, but it is %s" % version_str
    return 'psana-conda-%s' % version_str

def psanaCondaSourceZipFilename(basedir, version_str):
    pkgName = psanaCondaPackageName(version_str)
    basename = pkgName + '.tar.gz'
    outputFile = os.path.join(basedir, 'downloads', 'anarel', basename)
    return outputFile

def psanaCondaRecipeDir(basedir, manageSubDir):
    path=os.path.join(basedir, manageSubDir, 'recipes', 'psana', 'psana-conda-opt')
    assert os.path.exists(path), "psana conda recipe dir: %s doesn't exist" % path
    return path

def standardPath():
    return '/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin:/usr/kerberos/bin'

def anaRelManagePath(basedir, manageSubDir):
    path = standardPath()
    managebin=os.path.join(basedir, manageSubDir, 'bin')
    assert os.path.exists(managebin), "path wrong: %s" % managebin
    path = '%s:%s' % (managebin, path)
    return path

def testCondaPath(basedir):
    path = standardPath()
    testbin = os.path.join(basedir, 'anarel-test')
    assert os.path.exists(testbin), "path %s doesn't exist" % testbin
    path = '%s:%s' % (testbin, path)
    return path

def condaPath(devel, osname, basedir, manageSubDir):
    path = anaRelManagePath(basedir, manageSubDir)
    conda=os.path.join(basedir, 'inst', 'miniconda2-')
    if devel:
        conda += 'dev-'
    else:
        conda += 'prod-'
    conda += '%s/bin' % osname
    if osname != '{OSNAME}':
        assert os.path.exists(conda), "path wrong: %s" % conda
    path = "%s:%s" % (conda,path)
    return path

def compareDicts(dictA,dictB):
    allkeys = list(set(dictA.keys()).union(set(dictB.keys())))
    allkeys.sort()
    report = {'new':[],'old':[],'changed':[], 'same':[]}
    for key in allkeys:
        if key in dictA and not (key in dictB):
            report['old'].append(dictA[key])
        elif not (key in dictA) and (key in dictB):
            report['new'].append(dictB[key])
        elif dictA[key] != dictB[key]:
            report['changed'].append({'old':dictA[key],
                                      'new':dictB[key]})
        elif dictA[key] == dictB[key]:
            report['same'].append(dictA[key])
    return report

def htmlPsanaDiffReports(psanaReport):
    html = ''
    html += '<h2>psana-conda</h2>\n'
    html += '<h3>version</h3>\n'
    oldVer = psanaReport['version']['old']
    newVer = psanaReport['version']['new']
    OLD_NEW = '''{old} --> {new}<br>\n'''
    if oldVer == newVer:
        html += "*WARNING* version is the same: %s" % oldVer
    else:
        html += OLD_NEW.format(old=oldVer, new=newVer)
    tags = psanaReport['tags']
    html += '<h3>tags</h3>\n'
    names = [ elem['name'] for elem in tags['old']]
    names.sort()
    names = [name.strip() for name in names if name.strip()]
    if len(names)>0:
        html += '<h4>dropped</h4>\n'
        for name in names:
            html += '%s<br>\n' % name

    if len(tags['new'])>0:
        html += '<h4>new</h4>\n'
        for new_tag in tags['new']:
            html += '%s  %s<br>\n' % (new_tag['name'], new_tag['tag'])

    listOfChanged = tags['changed']
    if len(listOfChanged)>0:
        html += '<h4>changed</h4>\n'
        html += '<table border="1">\n'
        html += '  <tr> <th>package</th> <th>old</th> <th></th> <th>new</th> </tr>\n'
        def cmpnames(aa,bb): return aa['new']['name'] < bb['new']['name']
        listOfChanged.sort(cmp=cmpnames)
        for changed in listOfChanged:
            name=changed['new']['name']
            oldtag = changed['old']['tag']
            newtag = changed['new']['tag']
            html += '  <tr><td>%s</td><td>%s</td><td>--></td><td>%s</td></tr>\n' % (name, oldtag, newtag)
        html += '</table>\n'
    return html

def formatPkgInfo(pkginfo):
    msg='%s=%s=%s' % (pkginfo['name'], pkginfo['version'], pkginfo['buildstr'])
    if pkginfo['channel']:
        msg += ' channel=%s' % pkginfo['channel']
    return msg

def htmlEnvDiffReports(envA, envB, pkgsReport, psanaReport):
    def replaceNoneWithDefaults(channel):
        if channel is None:
            return 'defaults'
        return channel

    html ='<h1>conda environment report</h1>\n'
    OLD_NEW = '''{old} --> {new}<br>\n'''
    html += OLD_NEW.format(old=envA, new=envB)
    if psanaReport:
        html += htmlPsanaDiffReports(psanaReport)
    html += '<h2>Environment Packages</h2>\n'
    if len(pkgsReport['old']):
        html += '<h3>Dropped</h3>\n'
        names = [el['name'] for el in pkgsReport['old']]
        for name in names:
            html += '%s<br>\n' % name
    if len(pkgsReport['new']):
        html += '<h3>New</h3>\n'
        pkglist = pkgsReport['new']
        for pkginfo in pkglist:
            html += '%s<br>\n' % formatPkgInfo(pkginfo)
    if len(pkgsReport['changed']):
        html += '<h3>Changed</h3>\n'
        html += '<table border="1">\n'
        html += '<tr> <th>package</th> <th>old</th> <th></th> <th>new</th> <th>channel</th> </tr>\n'
        changelist = pkgsReport['changed']
        for changeinfo in changelist:
            oldinfo, newinfo = changeinfo['old'], changeinfo['new']
            name = oldinfo['name']
            oldver = '%s=%s' % (oldinfo['version'], oldinfo['buildstr'])
            newver = '%s=%s' % (newinfo['version'], newinfo['buildstr'])
            oldchannel = replaceNoneWithDefaults(oldinfo['channel'])
            newchannel = replaceNoneWithDefaults(newinfo['channel'])
            channelstr = ''
            if oldchannel != newchannel:
                channelstr = "%s --> %s" % (oldchannel, newchannel)
            else:
                channelstr = newchannel
            html += '  <tr> <td>%s</td> <td>%s</td> <td> --> </td> <td>%s</td> <td>%s</td> </tr>\n' % (name, oldver, newver, channelstr)
        html += '</table>\n'
    return html

def getPsanaReport(envA, envB, basedir):
    condaInstall = whichCondaInstall(basedir)
    relinfo = {}
    for env in [envA,envB]:
        pyfile = os.path.join(basedir, 'inst', condaInstall, 'envs', env, 'lib', 'python2.7', 'site-packages', 'anarelinfo', '__init__.py')
        assert os.path.exists(pyfile), "doesn't exist: %s" % pyfile
        relinfo[env]={}
        relinfo[env]['pyfile']=pyfile
        relinfo[env]['globals']={}
        relinfo[env]['locals']={}
        execfile(pyfile, relinfo[env]['globals'], relinfo[env]['locals'])
        pkgtags = {}
        for pkg, tag in relinfo[env]['locals']['pkgtags'].iteritems():
            pkgtags[pkg]={'name':pkg, 'tag':tag}
        relinfo[env]['locals']['pkgtags'] = pkgtags

    report={'version':{},
            'tags':{'same':[],'new':[],'old':[],'changed':[]}
        }
    report['version']['old']=relinfo[envA]['locals']['version']
    report['version']['new']=relinfo[envB]['locals']['version']
    report['version']['same']=report['version']['old']==report['version']['new']

    report['tags'] = compareDicts(relinfo[envA]['locals']['pkgtags'],
                                  relinfo[envB]['locals']['pkgtags'])
    return report

def diffEnvs(envA, envB, basedir):
    assert envA != envB, "diffEnvs: can't compare two environments that are the same - both are %s" % envA

    pkgsA={}
    pkgsB={}

    for envName, envPkgs in zip([envA, envB],
                                [pkgsA,pkgsB]):
        cmd = "conda list --name %s --json"  % envName
        stdout = run_command(cmd, stderr_in_stdout=True, quiet=True)
        pkgsList = json.loads(stdout)
        assert isinstance(pkgsList, list), "error running command:\n%s,json is not list, it is:\n%s" % (cmd, str(pkgsList))
        for pkgDict in pkgsList:
            pkgName, pkgVer, buildstr = pkgDict['name'], pkgDict['version'], pkgDict['build_string']
            channel = pkgDict['channel']
            if pkgName in envPkgs:
                warning("json output for env=%s has this package twice: %s, overwritting last=%s" % (envName, pkgName, envPkgs[pkgName]))
            envPkgs[pkgName]={'name':pkgName, 'channel':channel, 'version':pkgVer, 'buildstr':buildstr}

    pkgsReport = compareDicts(pkgsA, pkgsB)

    psanaReport = None
    if 'psana-conda' in pkgsA and 'psana-conda' in pkgsB:
        psanaReport = getPsanaReport(envA, envB, basedir)

    print(htmlEnvDiffReports(envA, envB, pkgsReport, psanaReport))

def manageJhubConfigKernel(cmd, envName, basedir, force):
    assert cmd in ['remove','create'], "cmd must be one of 'remove','create', not %s" % cmd
    assert envName, "envName invalid"
    assert basedir and os.path.exists(basedir), "--basedir does not specify path that exists, it is %s" % basedir
    jhubConfigDir = os.path.join(basedir, 'jhub_config')
    assert os.path.exists(jhubConfigDir), "The jhub config dir doesn't exist, tried: %s" % jhubConfigDir

    condaInstall = whichCondaInstall(basedir)
    assert condaInstall.startswith('miniconda2-'), "expected condaInstall=%s to start with miniconda2-" % condaInstall
    shortInstall = condaInstall.split('miniconda2-')[1]

    kernelEnvDir = jhubConfigDir
    for subdir in [shortInstall, 'kernels', envName]:
        kernelEnvDir = os.path.join(kernelEnvDir, subdir)
        if not os.path.exists(kernelEnvDir):
            if cmd == 'remove':
                print("manageJhubConfigKernel cmd==remove but dir=%s doesn't exist, not deleting anything" % kernelEnvDir)
                return
            print("Creating path: %s" % kernelEnvDir)
            os.mkdir(kernelEnvDir)

    outFilename = os.path.join(kernelEnvDir, 'kernel.json')
    if cmd == 'remove':
        if os.path.exists(outFilename):
            os.unlink(outFilename)
            print("removed %s" % outFilename)
        else:
            print("file %s doesn't exist" % outFilename)
        return

    if os.path.exists(outFilename) and not force:
        error("The jhub kernel file: %s already exists. Use --force to overwrite" % outFilename)

    pyVer = 2
    if envName.endswith('-py3'):
        pyVer = 3

    envDir = getEnvRootDir(os.path.join(basedir, 'inst', condaInstall), envName)
    assert os.path.exists(envDir), "dir %s doesn't exist - not going to setup jhub kernel for environment that doesn't exist" % envDir

    pyBin = os.path.join(envDir, 'bin', 'python')
    assert os.path.exists(pyBin), "jhub config - python binary %s doesn't exist" % pyBin

    sit_data = ':'.join([os.path.join(envDir, 'data'),
                         '/reg/g/psdm/data'])

    data = {"display_name": "Python %d %s" % (pyVer, envName),
            "language": "python",
            "argv": [pyBin,
                     "-m",
                     "ipykernel",
                     "-f",
                     "{connection_file}"],
            "env": {"SIT_DATA": sit_data,
                    "SIT_ROOT": "/reg/g/psdm", "LD_LIBRARY_PATH": ""}
        }

    with open(outFilename,'w') as fout:
        json.dump(data, fout, sort_keys=True,
                  indent=4, separators=(',', ': '))
    print("Wrote %s" % outFilename)

if __name__ == '__main__':
    diffEnvs('ana-1.0.3','ana-1.0.5', '/reg/g/psdm/sw/conda')
