from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import datetime
import time
import anarelmanage.util as util

def logMsg(msg, logFile):
    print(msg)
    if logFile:
        f = file(logFile,'a')
        f.write(msg)
        f.close()
        
def logOutput(cmd, logFile):
    logMsg("cmd: %s" % cmd, logFile)
    if logFile:
        cmd += ''' 2>&1 | tee -a %s''' % logFile
    sys.stderr.flush()
    sys.stdout.flush()
    os.system(cmd)
    sys.stderr.flush()
    sys.stdout.flush()


class PackageBuilder(object):

    def __init__(self, 
                 basedir,
                 channel,
                 channel_output_dir,
                 pkg,
                 pkgsubdir,
                 recipe_path,
                 logdir,
                 overwrite,
                 operating_system,
                 platform,
                 python_ver,
                 numpy_ver,
                 xtra_build_args,
                 opt,
                 warn_if_exists,
                 nolog,
                 dbg):

        self.basedir=basedir
        self.channel=channel
        self.channel_output_dir=channel_output_dir
        self.pkg=pkg
        self.pkgsubdir=pkgsubdir
        self.recipe_path=recipe_path
        self.logdir=logdir
        self.overwrite = overwrite
        self.os = operating_system
        self.platform = platform
        self.python_ver = python_ver
        self.numpy_ver = numpy_ver
        self.xtra_build_args=xtra_build_args
        self.opt = opt
        self.warn_if_exists = warn_if_exists
        self.nolog = nolog
        self.dbg = dbg
        assert not (self.opt and self.dbg), "can't specify both a opt and dbg build"

    def run(self):
        packageFileName = self.getPackageFileName()
        dest = os.path.join(self.channel_output_dir, os.path.basename(packageFileName))
        if os.path.exists(dest) and not self.overwrite:
            msg = "this build script will create the package file: %s\n However it already exists. Use --force to overwrite, or update the build script. " % dest
            if self.warn_if_exists:
                print("WARNING: %s" % msg)
                return True
            else:
                print("ERROR: %s" % msg)
                return False

        isPresent = util.removeIfPresent(packageFileName)
        if isPresent:
            # should be in conda-bld/linux-64, re-index
            pkgDir = os.path.split(packageFileName)[0]
            if os.path.exists(pkgDir):
                os.system("conda-index %s" % pkgDir)
                
        logFile = self.getLogFilename(packageFileName)
        t0 = time.time()
        if logFile:
            fout = file(logFile,'w')
            print("starting log file: %s" % logFile)
        else:
            fout = sys.stdout
        fout.write("############################\n")
        fout.write("## ana-rel-admin - PackageBuilder\n")        
        fout.write("## time: %s\n" % datetime.datetime.now())
        fout.write("## packageFileName: %s\n" % packageFileName)
        fout.write("## basedir = %s\n" % self.basedir)
        fout.write("## channel = %s\n" % self.channel)
        fout.write("## channel_output_dir = %s\n" % self.channel_output_dir)
        fout.write("## pkg = %s\n" % self.pkg)
        fout.write("## pkgsubdir = %s\n" % self.pkgsubdir)
        fout.write("## recipe_path = %s\n" % self.recipe_path)
        fout.write("## os = %s\n" % self.os)
        fout.write("## platform = %s\n" % self.platform)
        fout.write("## xtra_build_args = %s\n" % self.xtra_build_args)
        fout.write("## \n## \n")
        if logFile:
            fout.close()
            
        self.runCondaBuild(logFile)
        tm = os.path.getctime(packageFileName)-t0
        success = os.path.exists(packageFileName) and tm>0
        logMsg("finished running conda build. success=%r tm=%d:%d" % (success, tm//60, tm%60), logFile)
        if logFile:
            logMsg("logfile=%s" % logFile, logFile)
        if success:
            self.copyPackageFile(packageFileName, logFile)
            self.updateChannelIndex(logFile)
            return True
        else:
            logMsg(cmd="echo '## failure, package file doesn't exist'",logFile=logFile)
            return False

    def copyPackageFile(self, packageFileName, logFile):
        assert os.path.exists(packageFileName), "package file %s doesn't exist" % packageFileName
        dest = os.path.join(self.channel_output_dir, os.path.basename(packageFileName))
        cmd = 'cp %s %s' % (packageFileName, dest)
        logOutput(cmd,logFile)
        assert os.path.exists(dest), "failed to copy package file to %s" % dest

    def updateChannelIndex(self, logFile):
        cmd = 'conda index %s' % self.channel_output_dir
        logOutput(cmd, logFile)

    def getPackageFileName(self):
        '''Get the name of the output package file that will be produced from
        the conda build.
        '''
        cmd = 'conda build %s' % self.xtra_build_args

        if self.python_ver:
            cmd += ' --python=%s' % (self.python_ver,)
        if self.numpy_ver:
            cmd += ' --numpy=%s' % (self.numpy_ver,)
        
        cmd += ' --output %s' % self.recipe_path
        stdout, stderr = util.run_command(cmd)
        stderr_no_warnings = util.strip_warnings_and_harmless_messages(stderr)
        assert len(stderr_no_warnings)==0, "channel=%s pkg=%s problem with cmd=%s: stderr=%s" % \
            (self.channel, self.pkg, cmd, stderr)
        packagefile = stdout.strip()
        return packagefile

    def runCondaBuild(self, logFile):
        dbgBuild = False
        assert not (self.opt and self.dbg), "can't specify both opt and dbg build"
        if (not self.opt):
            if self.dbg or self.recipe_path.endswith('dbg'):
                dbgBuild = True
        sitvars = util.getSITvariables(debug=dbgBuild)
        cmd = 'SIT_ARCH=%s conda build' % sitvars['SIT_ARCH']
        if self.python_ver:
            cmd += ' --python=%s' % self.python_ver
        if self.numpy_ver:
            cmd += ' --numpy=%s' % self.numpy_ver
        cmd += ' %s' % self.xtra_build_args
        # if we don't put our channels first, we can pick
        # up packages from locals - i.e, the conda-build
        # workspace, would rather get them from channels
        for fileChannel in ['system', 'psana', 'external']:
            cmd += ' -c file://%s/channels/%s-%s' % (self.basedir, fileChannel, self.os)
#        if self.os == 'rhel5':
            ## currently, with conda 4.2.14, there is a bug: https://github.com/conda/conda-build/issues/1648            
            ## on rhel5
            ## but per https://github.com/slaclab/anarel-manage/issues/6
            ## this isn't enough, we're at conda 4.2.13 in rhel5
 #           cmd += ' --no-test'
        cmd += ' --quiet %s' % self.recipe_path
        logOutput(cmd, logFile)

    def getLogFilename(self, packageFileName):
        if self.nolog:
            return None
        logbase = os.path.basename(packageFileName)
        assert logbase.endswith('.tar.bz2'), "logbase doesn't end with .tar.bz2, it is %s" % logbase
        logbase = logbase[0:-8]
        logbase = 'conda_build_' + '_'.join([self.channel, logbase, self.os, self.platform])
        log = os.path.join(self.logdir, logbase + '.log')
        if self.overwrite or (not os.path.exists(log)):
            return log
        else:
            num = -1
            while True:
                num += 1
                logNum = os.path.join(self.logdir, logbase + ('_%2.2d.log' % num))
                if os.path.exists(logNum):
                    continue
                return logNum

    def anacondaUpload(self):
        packageFileName = self.getPackageFileName()
        fullPathToPackageFile = os.path.join(self.channel_output_dir, os.path.basename(packageFileName))
        if not os.path.exists(fullPathToPackageFile):
            print("ERROR: anacondaUpload: the package file %s doesn't exist, can't upload" % packageFileName)
            return

        print("file %s exists, will upload" % fullPathToPackageFile)
        user = 'lcls-%s' % self.os
        cmd = 'anaconda upload -u %s ' % user
        cmd += fullPathToPackageFile
        print("###### about to execute: #####")
        print(cmd)
        os.system(cmd)

### factory function
def makePackageBuilderFromArgs(args):
    def is_py3recipe(recipe):
        if recipe.endswith('-py3'): return True
        if recipe.find('-py3-')>0: return True
        if recipe.find('-py3_')>0: return True
        if recipe.find('_py3-')>0: return True
        if recipe.find('_py3_')>0: return True
        return False
    
    assert args.recipe is not None, "must supply -r with recipe dir"
    assert os.path.exists(args.recipe), "recipe path doesn't exist: %s" % args.recipe
    assert os.path.isdir(args.recipe), "%s is not a directory" % args.recipe
    assert os.path.exists(os.path.join(args.recipe, 'meta.yaml')), \
        "there is no meta.yaml in %s" % args.recipe
    if is_py3recipe(args.recipe):
        if args.python is None:
            print("detecting a py3 recipe, seeting args.python to 3.5")
            args.python='3.5'
    channeldir = os.path.split(os.path.abspath(args.recipe))[0]
    channel = os.path.split(channeldir)[1]
    channel_output_dir = os.path.join(args.basedir, 
                                      'channels',
                                      '%s-%s' % (channel, args.os),
                                      args.platform)
    assert os.path.exists(channel_output_dir), \
        "channel output dir=%s for recipe=%s doesn't exist" % \
        (channel_output_dir, args.recipe)

    logDir = os.path.join(args.basedir, 'logs')
    assert os.path.exists(logDir), "log dir %s doesn't exist" % logDir

    pkgsubdir = os.path.split(args.recipe)[1]
    pkg = pkgsubdir.split('-')[0]
    pkgBuilder = PackageBuilder(basedir=args.basedir,
                                channel=channel, 
                                channel_output_dir=channel_output_dir,
                                pkg=pkg,
                                pkgsubdir=pkgsubdir,
                                recipe_path=args.recipe,
                                logdir = logDir,
                                overwrite=args.force,
                                operating_system=args.os,
                                platform=args.platform,
                                python_ver=args.python,
                                numpy_ver=args.numpy,
                                xtra_build_args=args.xtra,
                                opt=args.opt,
                                warn_if_exists=args.warn_if_exists,
                                nolog = args.nolog,
                                dbg=args.dbg)
    return pkgBuilder

