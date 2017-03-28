from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys
import datetime
import time
from collections import defaultdict
import anarelmanage.util as util
import yaml

##### helper functions ############
def pkgsInVariant(pkglist, variant, osname):
    pkgs = {}
    if variant == '':
        variant = 'bld'

    for pkg, pkginfo in pkglist.iteritems():
        if 'limit_os' in pkginfo:
            cant_install_this_os = True
            oslist = pkginfo['limit_os'].split(',')
            for ok_os in oslist:
                if osname == ok_os:
                    cant_install_this_os = False
            if cant_install_this_os:
                print("filtering package=%s since osname=%s and 'limit_os' key is %s" % 
                      (pkg, osname, pkginfo['limit_os']))
                continue
        if 'only_in_variant' in pkginfo:
            if pkginfo['only_in_variant'] == variant:
                pkgs[pkg]=pkginfo
            continue
        if variant in pkginfo:
            if pkginfo[variant] == 'skip':
                continue
        pkgs[pkg]=pkginfo
    return pkgs

def extractChannel(pkglist):
    '''a step can have a number of packages from a specific channel,
    all packages in the step must be from that channel
    '''
    if len(pkglist)==0: return None

    chl2pkgs = defaultdict(list)
    for pkg, pkginfo in pkglist.iteritems():
        chl = pkginfo.get('chl',None)
        chl2pkgs[chl].append(pkg)
    assert len(chl2pkgs)==1, "There is more than one channel specified in this pkglist, pkglist=%r, chl2pkgs=%r" % (pkglist, chl2pkgs)
    return chl2pkgs.keys()[0]


############# MAIN CLASS #############
class ReleaseBuilder(object):

    def __init__(self, 
                 basedir,
                 logdir,
                 swGroup,
                 operating_system,
                 platform,
                 checkpoint,
                 variant,
                 stage,
                 force,
                 inter,
                 dev,
                 nolog,
                 name):

        self.basedir=basedir
        self.logdir=logdir
        self.swGroup=swGroup
        self.osname = operating_system
        self.checkpoint = checkpoint
        self.platform = platform
        self.name = name
        self.variant = variant
        self.force = force
        self.inter = inter
        self.stage = stage
        self.dev = dev
        self.nolog = nolog
        assert self.name, "must provide a base name for new %s-rel" % self.swGroup
        if not self.name.startswith('%s-' % self.swGroup):
            assert self.force, "The new %s release name does not start with '%s-'. If you want to proceed with this non-standard name, add the --force option" % (self.swGroup, self.swGroup)
                
        assert self.stage >=1, "stages start at 1, but stage=%d" % self.stage

        if self.swGroup == 'ana':
            all_variants = ['', 'py3', 'gpu']
        else:
            all_variants = ['']
        if self.variant is not None:
            if self.variant == 'bld':
                all_variants = ['']
            else:
                assert self.variant in all_variants, "unknown variant=%s, must be one of: bld py3 dbg gpu" % self.variant
                all_variants = [ self.variant ]

        if len(self.name.split('-'))>2:
            specified_variant = self.name.split('-')[-1]
            assert specified_variant in all_variants[1:], "The release name: %s has more than 1 '-' character, it seems to specify a release variant of %s, this is not a known variant, known variants=%s" % \
                (self.name, specified_variant, all_variants[1:])
            self.variants = [specified_variant]
        else:
            self.variants = all_variants

        envRoot, envs = util.condaEnvs()
        for variant in self.variants:
            if len(variant):
                relname = '-'.join([self.name, variant])
            else:
                relname = self.name
            if self.stage==1:
                assert relname not in envs, "There is already a conda environment named: %s, aborting" % relname
            else:
                assert relname in envs, "can't start at stage %d, no conda environment named: %s, aborting" % (self.stage, relname)
        self.isProductionInstall = util.whichCondaInstall(self.basedir).find('-dev-rhel')<0

    def makeCommandWithLogging(self):
        cmd = 'ana-rel-admin --cmd newrel --%s --xx --basedir %s' % (self.swGroup, self.basedir)
        if self.force:
            cmd += ' --force'
        cmd += ' --os %s' % self.osname
        if self.checkpoint:
            cmd += ' --checkpoint'
        cmd += ' --name %s' % self.name
        if self.variant:
            cmd += ' --variant %s' % self.variant
        if self.dev:
            cmd += ' --dev'
        if self.nolog:
            cmd += ' --nolog'
        cmd += ' --stage %d' % self.stage
        logfile = self.getLogFilename()
        if logfile:
            cmd += " | tee %s" % logfile
        sys.stderr.flush()
        print(cmd)
        sys.stdout.flush()
        return cmd

    def getLogFilename(self):
        if self.nolog:
            return None
        inst = util.whichCondaInstall(self.basedir)
        logfile = os.path.join(self.logdir, 'build-%s-%s.log' % (self.name, inst))
        if self.force:
            sys.stderr.write("WARNING: logfile %s exists, will overwrite it.\n" % logfile)
        return logfile
        dig = 0
        while os.path.exists(logfile):
            logfile = os.path.join(self.logdir, 'build-%s-%s-%2.2d.log' % (self.name, inst, dig))
            dig += 1
        return logfile

    def run(self):
        print("############################")
        print("## Release Builder - name=%s\n" % self.name)
        print("## time: %s\n" % datetime.datetime.now())
        basename = 'anarel.yaml'
        if self.dev:
            basename += '-tst'
        anarelyaml = util.getFile('config',basename)
        self.logAndPrint("reading in %s" % anarelyaml)
        self.anaRelBuild = yaml.load(file(anarelyaml,'r'))
        self.verifyAnaRelYaml(self.anaRelBuild)

        self.logAndPrint("---------- yaml contents -------")
        self.logAndPrint(str(self.anaRelBuild))

        stage01 = self.anaRelBuild.pop(0)

        for variant in self.variants:
            if variant == 'gpu' and self.osname != 'rhel7':
                self.logAndPrint("-- skipping variant gpu on os=%s" % self.osname)
                continue
            if variant in ['gpu','dbg'] and self.isProductionInstall:
                self.logAndPrint("--skipping variant %s since this is production install" % variant)
                continue
            relname = self.relNameFromVariant(variant)
            stageOnePkgs = self.createNewAnaRel(relname, stage01, variant)            
            self.logAndPrint("------ relname=%s variant=%s stage 01 complete ---------" % (relname, variant))
            if self.checkpoint:
                stage01_checkpoint_file, numStage1Files = util.checkPoint(self.basedir, relname, 'stage01')
                self.logAndPrint("------ relname=%s variant=%s stage 01 checkpoint file = %s numfiles=%d---------" % (relname, variant, stage01_checkpoint_file, numStage1Files))
            if self.checkpoint:
                prev_checkpoint_file = stage01_checkpoint_file
            for idx, stage in enumerate(self.anaRelBuild):
                stageNum = 2 + idx
                self.addPkgsToAnaRel(relname, stage, variant)
                self.logAndPrint("------ relname=%s variant=%s stage %d complete ---------" % (relname, variant, stageNum))
                if self.checkpoint:
                    current_checkpoint_file, numFiles = util.checkPoint(self.basedir, relname, 'stage%0.2d' % stageNum)
                    self.logAndPrint("------ relname=%s variant=%s stage %d checkpoint file = %s numfiles=%d ---------" % (relname, variant, stageNum, current_checkpoint_file, numFiles))
                if self.checkpoint:
                    checkpointResult = util.compareCheckPointFiles(prev_checkpoint_file, current_checkpoint_file, return_string=True)
                    self.logAndPrint("------- results of checkpoint comparision --------")
                    self.logAndPrint(checkpointResult)
                    self.logAndPrint("--------------------------------------------------")
                    prev_checkpoint_file = current_checkpoint_file
            envRoot, envs = util.condaEnvs()
            assert relname in envs, "relname=%s not in envs=%s" % (relname, envs)
            envDir = os.path.join(envRoot, relname)
            util.createSitVarsCondaEnv(dbg= variant=='dbg', force=True, envDir=envDir)
            util.manageJhubConfigKernel(cmd='create', envName=relname, 
                                        basedir=self.basedir, force=self.force)
            if variant == 'gpu':
                util.addToActivateDeactivateGPUVariables(envDir=envDir)
            self.logAndPrint("--- checking/fixing any permission issues ---")
            util.checkFixPermissions(envDir)
        self.logAndPrint("== SUCCESS == anrel=%s all variants and stages complete" % (self.name))
        return True

    def relNameFromVariant(self, variant):
        if len(variant):
            relname = '-'.join([self.name, variant])
        else:
            relname = self.name
        return relname

    def verifyAnaRelYaml(self, yamlContents):
        assert isinstance(yamlContents, list), "yaml not a list"
        assert len(yamlContents)>0, "no stages in yaml"

        pkgsSeen = []
        for stageNum, stage in enumerate(yamlContents):
            for pkg, pkginfo in stage.iteritems():
                assert pkg not in pkgsSeen, "pkg=%s appears multiple times in yaml" % pkg
                pkgsSeen.append(pkg)
                extractChannel(stage) # throws exception if more than one
                assert 'ver' in pkginfo.keys(), "pkg=%s stage=%d doesn't have ver key" % (pkg, stageNum)
                assert isinstance(pkginfo['ver'],str), "pkg=%s stage=%d, 'ver' is not a string, cannot specify a number, ie, instead of 4.1 write '=4.1'" % \
                    (pkg, stageNum)
                assert pkginfo['ver'].startswith('>') or \
                    pkginfo['ver'].startswith('=') or \
                    pkginfo['ver']=='latest', "pkginfo for pkg=%s has a 'ver' key but it doesn't start with > or = or latest" % pkg
                for ky in pkginfo.keys():
                    assert ky in ['limit_os', 'py3ver', 'ver','bld','dbg','py3','gpu','chl', 'only_in_variant'], "unknown yaml key=%s for pkg=%s in stage=%d" % \
                        (ky, pkg, stageNum)
                if 'only_in_variant' in pkginfo:
                    assert pkginfo['only_in_variant'] in ['dbg','gpu','py3','opt'], "allowable values for 'only_in_variant' are ['dbg','gpu','py3',opt'], but for pkg=%s in step=%d the value is %s" % \
                        (pkg, stageNum, pkginfo['only_in_variant'])

    def logAndPrint(self, msg):
        sys.stdout.flush()
        sys.stderr.flush()
        print(msg)
        sys.stdout.flush()

    def makePackageString(self, pkg, pkginfo, variant):
        '''assumed pkg lives in this variant.
        Reads the version from the package info. The same version is used
        for all variants. If the variant is in pkginfo, it specifies the build
        string.
        '''
        def getVersion(pkginfo, variant):
            if variant == 'py3':
                if 'py3ver' in pkginfo:
                    return pkginfo['py3ver']
            return pkginfo['ver']

        if variant == '':
            variant = 'bld'
        pkgstr = pkg
        version = getVersion(pkginfo, variant)
        if version == 'latest':
            assert variant not in pkginfo, "the version is latest but a build string is specified, pkg=%s pkginfo=%s" % (pkg, pkginfo)
            return pkgstr
        pkgstr += version
        if variant in pkginfo:
            pkgstr += '=%s' % pkginfo[variant]
        return pkgstr

    def createNewAnaRel(self, conda_env_name, pkglist, variant):
        self.logAndPrint("----- %s -----" % conda_env_name)

        # create new environment with given name
        cmd = 'conda create'
        if not self.inter:
            cmd += ' -y -q'
        cmd += ' -n %s' % conda_env_name

        # add python, check if python 3
        cmd += ' python'
        if variant == 'py3':
            cmd += '=3.5'

        pkglist = pkgsInVariant(pkglist, variant, self.osname)
        chl = extractChannel(pkglist)
        assert chl is None, "no special channel for first stage, but chl=%s" % chl

        # add packages in pkglist
        for pkg, pkginfo in pkglist.iteritems():
            pkgString = self.makePackageString(pkg, pkginfo, variant)
            cmd += ' %s' % pkgString
        self.logAndPrint(cmd)

        # run conda command to create environment
        res = os.system(cmd)
        assert res == 0, "cmd %s failed, retcode=%d" % (cmd, res)
        time.sleep(.2)

    def addPkgsToAnaRel(self, conda_env_name, pkglist, variant):
        pkglist = pkgsInVariant(pkglist, variant, self.osname)
        if len(pkglist)==0:
            self.logAndPrint("---- no pkgs for this step, variant=%s ---" % variant)
            return []

        self.logAndPrint("----- adding pkgs to %s -----" % conda_env_name)
        cmd = 'conda install'
        if not self.inter:
            cmd += ' -y -q'
        cmd += ' -n %s' % conda_env_name

        chl = extractChannel(pkglist)
        if chl:
            cmd += ' -c %s' % chl

        for pkg, pkginfo in pkglist.iteritems():
            pkgString = self.makePackageString(pkg, pkginfo, variant)
            if pkgString:
                cmd += ' %s' % pkgString
        self.logAndPrint(cmd)
        res = os.system(cmd)
        assert res==0, "cmd %s failed, retcode=%d" % (cmd, res)
        time.sleep(.2)
        return pkglist.keys()

### factory function
def makeReleaseBuilderFromArgs(args):
    logDir = os.path.join(args.basedir, 'logs')
    assert os.path.exists(logDir), "log dir %s doesn't exist" % logDir

    assert args.ana or args.dm, "must specify one of --ana or --dm"
    assert not (args.ana and args.dm), "can't specify both --ana and --dm"

    if args.ana:
        swGroup = 'ana'
    elif args.dm:
        swGroup = 'dm'

    assert args.name, "must provide a name for ana release, like %s-1.0.0." % swGroup
    
    relBuilder = ReleaseBuilder(basedir=args.basedir,
                                logdir = logDir,
                                swGroup = swGroup,
                                operating_system=args.os,
                                platform=args.platform,
                                checkpoint=args.checkpoint,
                                variant=args.variant,
                                stage=args.stage,
                                force=args.force,
                                inter=args.inter,
                                dev=args.dev,
                                nolog=args.nolog,
                                name=args.name)
    return relBuilder

