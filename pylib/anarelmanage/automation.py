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
import paramiko as pm
import getpass
import shutil
import smtplib
from email.mime.text import MIMEText

FAILURE_MSG='''
ana-rel-admin AUTO command has *FAILED* for
{anaVer} on step {step}.

master log file at {master_log_file}

link: https://pswww.slac.stanford.edu/user/psreldev/builds/auto-{version}/
'''
SUCCESS_MSG='''
ana-rel-admin AUTO command has *SUCCEEDED* for
{anaVer}.

master log file at {master_log_file}

link: https://pswww.slac.stanford.edu/user/psreldev/builds/auto-{version}/

prod py27 report: https://pswww.slac.stanford.edu/user/psreldev/builds/auto-{version}/release_notes_py27_prod-rhel7.html

prod py3 report: https://pswww.slac.stanford.edu/user/psreldev/builds/auto-{version}/release_notes_py3_prod-rhel7.html

When ready, have admin account execute:

ana-rel-admin --cmd change-current --%s --name {swVer}

and 

ana-rel-admin --cmd anaconda-upload --recipe {psanaCondaRecipeDir}

to upload psana-conda={version} to the lcls channels.
'''
class AutoReleaseBuilder(object):
    def __init__(self, name, swGroup, force, clean, tagsfile, basedir, manageSubDir, dev, email, variant):
        self.version_str = name
        self.swGroup = swGroup
        self.force = force
        self.clean = clean
        self.tagsfile = util.getPsanaTagsFile(tagsfile)
        self.basedir = os.path.abspath(basedir)
        self.manageSubDir = manageSubDir
        self.variant = variant
        self.email = email
        self.dev = dev
        self.needs_testing = None

        if dev:
            self.tagsfile += '-tst'

        assert os.path.exists(self.tagsfile), "tagsfile: %s doesn't exist" % self.tagsfile
        assert os.path.exists(self.basedir), "basedir: %s doesn't exist" % self.basedir

        self.logDir = None
        self.testerLogDir = None
        self.logFname = None
        self.masterLog = None
        
        self.steps = []

        self.psanaPkgName = None
        self.relName = None

        self.ssh = {'rhel5':{'host':'psdev106',
                             'build':None,
                             'test':None},
                    'rhel6':{'host':'psdev105',
                             'build':None,
                             'test':None},
                    'rhel7':{'host':'psel701',
                             'build':None,
                             'test':None}
                }

        self.setNames()
        self.startLogDir() 
        self.updateRecipe()

        ana_all_steps=[
            # single host/ name/ function
            (True,  'source_tags',    self.source_tags),
            (False, 'build_psana',    self.build_psana),
            (False, 'dev_envs',       self.dev_envs),
            (False, 'test_dev_envs',  self.test_dev_envs),
            (False, 'prod_envs',      self.prod_envs),
            (False, 'test_prod_envs', self.test_prod_envs),
            (False,  'release_notes_py27_prod',  self.release_notes_py27_prod),
            (False,  'release_notes_py3_prod',  self.release_notes_py3_prod),
            (False,  'release_notes_py27_dev',  self.release_notes_py27_dev),
            (False,  'release_notes_py3_dev',  self.release_notes_py3_dev),
            (False,  'release_notes_gpu_dev',  self.release_notes_gpu_dev),
        ]

        dm_all_steps=[
            # single host/ name/ function
            (False, 'prod_envs',      self.prod_envs),
            (False,  'release_notes_py27_prod',  self.release_notes_py27_prod),
        ]

        if swGroup == 'ana':
            all_steps = ana_all_steps
            self.needs_testing = True
        elif swGroup == 'dm':
            all_steps = dm_all_steps
            self.needs_testing = False

        steps_todo = self.identifySteps(all_steps)

        self.ssh_connections(self.needs_testing)
        self.executeSteps(steps_todo)
        self.successNotify()

    def add_opts(self, cmd):
        cmd += ' --basedir %s' % self.basedir
        cmd += ' --tagsfile %s' % self.tagsfile
        if self.force:
            cmd += ' --force'
        if self.variant:
            cmd += ' --variant %s' % self.variant
        return cmd

        
    def ssh_connections(self, needs_testing):
        build_user = os.environ['USERNAME']
        if needs_testing:
            test_user = os.environ.get('SUDO_USER',build_user)
            if test_user == build_user:
                test_user = os.environ.get('USER',build_user)
            assert test_user != build_user, ("cannot find a test_user differnt than " + \
                   "build user=%s. Tried SUDO_USER and USER. Ordinarily, you sudo as " + \
                   "psreldev (the build user) but this script uses the environment " + \
                   "variable SUDO_USER to figure out who you really are, and that is " + \
                   "who is used to test built installations. To fix, set SUDO_USER to " + \
                   "your username") % build_user

            print("--- AUTO ----------")
            print("enter password for test_user: %s" % test_user)
            print("this is not echoed to screen, but is stored in python string.")
            test_user_password = getpass.getpass("The string will be deleted in a few seconds: ")
        for osname, sshdict in self.ssh.iteritems():
            ssh_build = pm.SSHClient()
            ssh_test = pm.SSHClient()

            ssh_build.set_missing_host_key_policy(pm.AutoAddPolicy())
            ssh_test.set_missing_host_key_policy(pm.AutoAddPolicy())

            host = sshdict['host']
            ssh_build.connect(host, username=build_user)
            if needs_testing:
                ssh_test.connect(host, username=test_user, password=test_user_password)

            sshdict['build']=ssh_build
            sshdict['test']=ssh_test

        if needs_testing:
            del test_user_password
        print("-- AUTO: ssh build and test (if needed) connections have been made.")

    def updateRecipe(self):
        recipeDir = util.psanaCondaRecipeDir(self.basedir, self.manageSubDir)
        renderedMetaFile = os.path.join(self.logDir, 'psana-conda-rendered.yaml.txt')
        cmd = 'conda-render -f %s %s' % (renderedMetaFile, recipeDir)
        if os.path.exists(os.path.join(self.logDir, 'recipe.success')):
            master = file(self.logFname,'a')
            master.write("<h2>psana conda recipe</h2>\n")
            master.write("** SUCCESS **  <a href=psana-conda-rendered.yaml.txt>psana-conda-rendered.yaml.txt</a><br>cmd= %s<br>\n" % cmd)
            master.close()
            return
        print("--AUTO: calling %s\nSo that the psana-conda recipe can be examined to check that the package version matches %s" % (cmd, self.version_str))
        sys.stdout.flush()
        sys.stderr.flush()
        assert 0 == os.system(cmd)
        meta = yaml.load(file(renderedMetaFile,'r'))
        assert meta['package']['name'] == 'psana-conda', "rendered meta.yaml for psana-conda package name is wrong"
        if meta['package']['version'] != self.version_str:
            print("--- AUTO: ERROR: You must update the meta.yaml to use version=%s in directory\n %s. Currently it is %s" % (self.version_str, recipeDir,  meta['package']['version']))
            sys.exit(0)
        f = file(os.path.join(self.logDir,'recipe.success'),'w')
        f.close()
        print("--- AUTO: psana-conda recipe has correct version.")
        sys.stdout.flush()

    def checkThatReleaseIsNewerThanCurrent(self):
        if self.variant is None:
            if self.swGroup == 'ana':
                variants = ['','gpu','py3']
            elif self.swGroup == 'dm':
                variants = ['']
        else:
            variants = ['']
        for variant in variants:
            current_fname = os.path.join(self.basedir, 'current', self.swGroup, '%s-current' % self.swGroup)
            if variant:
                current_fname += '-%s' % variant
            current = file(current_fname).read().strip()
            assert self.relName.startswith('%s-' % self.swGroup)
            assert current.startswith('%s-' % self.swGroup)
            verCur = current.split('%s-' % self.swGroup)[1]
            verNew = self.relName.split('%s-' % self.swGroup)[1]
            variantName = variant
            if not variantName: variantName = 'normal'
            assert util.versionGreater(verNew, verCur), "For variant: %s, " + \
                "the %s version being build is not greater than what is in " + \
                "%s-current. Aborting. Version requested=%s, but ana current " + \
                "version (for this variant) is %s" %  (variantName, self.swGroup, self.swGroup, 
                                                       verNew, verCur)

    def checkThatAnaRelYamlHasCorrectPsanaCondaVersion(self):
        if self.dev: return True
        anarelyaml = util.getFile('config', 'anarel.yaml')
        relbuild = yaml.load(file(anarelyaml,'r'))
        found = False
        for stage in relbuild:
            if 'psana-conda' in stage:
                found = True
                pkginfo = stage['psana-conda']
                verstr = pkginfo['ver']
                assert verstr.startswith('='), 'psana-conda verstr from %s is %s, should start with =' % (anrelyaml, verstr)
                ver = verstr[1:]
                assert ver==self.version_str, "ERROR: version mismatch. " + \
                    "anarelyaml={ver} != build={anaver}.\n" + \
                    "You need to update the psana-conda version to " + \
                    "{anaver} in the file {fname}".format(ver=ver, anaver=self.version_str, fname=anarelyaml)

        assert found, "went through %d stages of %s, did not find psana-conda package" % (len(relbuild), anarelyaml)

    def setNames(self):
        assert util.validVersionStr(self.version_str), "--name must specify valid version string, i.e, n.n.n or n.n.nxxx, but it is %s" % self.version_str
        self.relName = '%s-%s' % (self.swGroup, self.version_str)

        self.checkThatReleaseIsNewerThanCurrent()
        if swGroup == 'ana':
            self.psanaPkgName = util.psanaCondaPackageName(self.version_str)
            self.checkThatAnaRelYamlHasCorrectPsanaCondaVersion()
        else:
            self.psanaPkgName = None

        print("########## AutoReleaseBuilder ############")
        if self.swGroup == 'ana':
            print("psana pkg name: %s" % self.psanaPkgName)
        print("%s release name: %s" % (self.swGroup, self.relName))
        if not os.environ.get('NOASK', False):
            res = raw_input("\nis this Ok? based on --name: ")
            if res.strip().lower() != 'y':
                print("exiting, y not received")
                sys.exit(1)

    def startLogDir(self):
        if self.needs_testing:
            self.testerLogDir = os.path.join(self.basedir, "tester_logs")
            assert os.path.exists(self.testerLogDir), "tester log dir: %s doesn't exist" % self.testerLogDir

        baseLogDir = '/reg/neh/home/psreldev/public_html/builds'
        assert os.path.exists(baseLogDir), "logdir %s doesn't exist" % baseLogDir
        logDir = os.path.join(baseLogDir, 'auto-%s-%s' % (self.swGroup, self.version_str))
        if os.path.exists(logDir):
            if self.clean:
                print("--- AUTO: old logDir exists, but --clean given, removing %s" % logDir)
                shutil.rmtree(logDir)
                
        if not os.path.exists(logDir):
            os.mkdir(logDir)
            print("--- AUTO: made directory %s" % logDir)
        else:
            print("--- AUTO: log directory %s exists, picking up where last AUTO failed" % logDir)
        self.logDir = logDir
        self.logFname = os.path.join(self.logDir, "index.html")
        if os.path.exists(self.logFname):
            print("--- AUTO: deleting old file: %s" % self.logFname)
            os.unlink(self.logFname)
        self.masterLog = file(self.logFname,'w')
        self.masterLog.write("<h1>AUTO %s-%s</h1>\n" % (self.swGroup, self.version_str))
        self.masterLog.write("starting log: %s<br>\n" % (datetime.datetime.now()))
        self.masterLog.close()

    def identifySteps(self, all_steps):
        def singleHostStep(self, name, fn, steps_todo):
            done = (not self.clean) and os.path.exists(os.path.join(self.logDir, "%s.success" % name))
            if done:
                master = file(self.logFname,'a')
                master.write("<h2>%s</h2>\n" % name)
                master.write("<a href=%s.txt>%s</a>: PICKUP - SUCCESS<br>\n" % (name, name))
                master.close()
            else:
                steps_todo.append((name,fn))

        def multipleHostStep(self, name, fn, steps_todo):
            successAll = True
            for osname in self.ssh:
                fname = os.path.join(self.logDir, '%s-%s.success' % (name, osname))
                if not os.path.exists(fname):
                    successAll = False
            if (not self.clean) and successAll:
                master = file(self.logFname,'a')
                master.write("<h2>%s</h2>\n" % name)
                master.write("PICKUP: sucess.<br>\n")
                for osname in self.ssh:
                    master.write("<a href=%s-%s.txt>%s-%s</a><br>\n" % (name, osname, name, osname))
                master.close()
            else:
                steps_todo.append((name,fn))
            
        ## end helpers
        steps_todo = []
        for singlehost, stepname, stepfn in all_steps:
            if singlehost:
                singleHostStep(self, name=stepname, fn=stepfn, steps_todo=steps_todo)
            else:
                multipleHostStep(self, name=stepname, fn=stepfn, steps_todo=steps_todo)
        return steps_todo

    def executeSteps(self, steps_todo):
        print("--- AUTO: executeSteps, there are %d steps to do" % len(steps_todo))
        t0 = time.time()
        for name,step in steps_todo:
            step(name=name)
        total_time = time.time()-t0
        minutes = int(total_time//60)
        seconds = int(round(total_time % 60))
        master = file(self.logFname,'a')
        master.write("<h1>Time</h1>")
        master.write("%d minutes, %d seconds<br>" % (minutes, seconds))
        master.close()
        
    def notify(self, hdr, msg, step=None):
        msg = msg.format(version=self.version_str,
                         anaVer=self.relName,
                         master_log_file=self.logFname,
                         psanaCondaRecipeDir=util.psanaCondaRecipeDir(self.basedir, self.manageSubDir),
                         step=step)

        msg=MIMEText(msg)
        msg['Subject'] = 'ana-rel-admin AUTO %s *%s*' % (self.relName, hdr)
        msg['From'] = '%s@slac.stanford.edu' %  os.environ.get('USERNAME','unknown')
        msg['To'] = self.email
        
        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        s = smtplib.SMTP('localhost')
        s.sendmail(msg['From'], [msg['To']], msg.as_string())
        s.quit()     
            
    def failureNotify(self, step):
        self.notify(hdr='FAIL', msg=FAILURE_MSG, step=step)

    def successNotify(self):
        self.notify(hdr='SUCCESS', msg=SUCCESS_MSG, step=None)

    def getStepLogFile(self, name, html, tester, osname=None):
        log = name
        if osname:
            log += '-%s' % osname
        if html:
            log += '.html'
        else:
            log += '.txt'
        if tester:
            full_log = os.path.join(self.testerLogDir, log)
        else:
            full_log = os.path.join(self.logDir, log)
        return full_log

    def commands_to_activate_env(self, devel, osname, env):
        cmds = 'unset PYTHONPATH; export PYTHONPATH'
        cmds += '; unset LD_LIBRARY_PATH; export LD_LIBRARY_PATH'
        cmds += '; export PATH=%s' % util.condaPath(devel=devel, 
                                                    osname=osname,
                                                    basedir=self.basedir,
                                                    manageSubDir=self.manageSubDir)
        cmds += '; sleep 1; source activate %s; sleep 1' % env
        return cmds

    def write_ssh_log(self, name, osname, res, logexists, logfilesize, stdout, stderr):
        basename = '%s-%s_ssh.txt' % (name, osname)
        fullname = os.path.join(self.logDir, basename)
        fout = file(fullname, 'w')
        fout.write("command result=%d logexists=%r log filesize=%d\n" % (res, logexists, logfilesize))
        fout.write("==stdout==\n")
        fout.write('\n'.join(stdout.readlines()))
        fout.write("\n==stderr==\n")
        fout.write('\n'.join(stderr.readlines()))
        fout.close()
        return basename
    
    def execute_step_from_current_host_env(self, name, cmd, html=False):
        t0 = time.time()
        print("-- AUTO %s" % name)

        master = file(self.logFname,'a')
        master.write("<h2>%s</h2>\n" % name)
        master.write("<h3>command</h3>\n")
        master.write("<pre>%s\n</pre>\n" % cmd)

        if html:
            log = os.path.join(self.logDir, "%s.html" % name)
        else:
            log = os.path.join(self.logDir, "%s.txt" % name)
            
        if os.path.exists(log):
            print("-- AUTO: removing old log file: %s" % log)
            os.unlink(log)
        cmd += " > %s 2>&1" % log
        print("-- AUTO: running %s" % cmd)        
        res = os.system(cmd)
        master.write("<a href=%s>%s</a>: " % (os.path.basename(log),name))
        if 0 != res:
            master.write(" ** FAIL **")
            master.close()
            print("-- AUTO: ** FAIL **")
            self.failureNotify(step=name)
            sys.exit(-1)
        else:
            total_time = time.time()-t0
            minutes = int(total_time//60)
            seconds = int(round(total_time % 60))
            master.write(" ** SUCCESS ** step time: %d minutes %d secs" % (minutes, seconds))
            print("-- AUTO: ** SUCCESS **")
            f=file(os.path.join(self.logDir,"%s.success" % name),'w')
            f.close()
        master.write('\n<br>')
        master.close()

    def _launch_multihost(self, name, cmd_or_cmddict, devel, env, html, tester):
        osname2exec = {}
        for osname, sshdict in self.ssh.iteritems():
            step_cmd = None
            if isinstance(cmd_or_cmddict,dict):
                if osname in cmd_or_cmddict:
                    step_cmd = cmd_or_cmddict[osname]
            else:
                step_cmd = cmd_or_cmddict
            if step_cmd is None:
                continue
            hostcmd = self.commands_to_activate_env(devel, osname, env)
            hostcmd += '; %s' % step_cmd
            logfile = self.getStepLogFile(name, html, tester, osname)
            hostcmd += ' > %s 2>&1' % logfile
            if tester:
                ssh = sshdict['test']
            else:
                ssh = sshdict['build']
            stdin, stdout, stderr = ssh.exec_command(hostcmd)
            execdict = {'stdin':stdin, 'stdout':stdout, 'stderr':stderr, 'log':logfile, 'hostcmd':hostcmd}
            osname2exec[osname]=execdict
        return osname2exec
    
    def _wait_multihost(self, name, launched, tester):
        ssh_results = {}
        for osname, execdict in launched.iteritems():
            logfile = execdict['log']
            loglink = os.path.basename(logfile)
            res = execdict['stdout'].channel.recv_exit_status()
            print("--- AUTO: %s-%s: finished exit code=%d" % (name, osname, res))
            execdict['exit_code']=res
            time.sleep(1)
            util.run_command('ls %s' % logfile)  # in case there are filesystem issues, stat file made an a different host
            logexists = os.path.exists(logfile)
            logfilesize = 0
            if logexists:
                logfilesize = os.path.getsize(logfile)
            ssh_log_link = self.write_ssh_log(name=name, osname=osname, res=res,
                                              logexists=logexists, logfilesize=logfilesize,
                                              stdout=execdict['stdout'],
                                              stderr=execdict['stderr'])
            ssh_results[osname]={'exit_code':res, 'ssh_link':ssh_log_link, 'loglink':None}
            if tester and logexists:
                autoLog = os.path.join(self.logDir, loglink)
                assert autoLog != logfile, "unexpected - log and autoLog file the same: %s" % logfile
                shutil.copyfile(logfile, autoLog)
                time.sleep(1)
                autosize = os.path.getsize(autoLog)
                assert autosize == logfilesize, "copied %s -->%s but old size=%d != new size=%d" % (logfile, autoLog, logfilesize, autosize)
                os.unlink(logfile)
                logfile = autoLog
            if logexists:
                ssh_results[osname]['loglink']=loglink
        return ssh_results
    
    def execute_multihost_step(self, name, devel, env, tester, cmd_or_cmddict, html):
        t0 = time.time()
        master = file(self.logFname,'a')
        master.write("<h2>%s</h2>\n" % name)

        launched = self._launch_multihost(name=name,
                                          cmd_or_cmddict=cmd_or_cmddict,
                                          devel=devel, env=env,
                                          html=html, tester=tester)
        master.write("<h3>commands</h3>\n")
        master.write("<pre>\n")
        for osname, execdict in launched.iteritems():
            master.write("%s: %s\n" % (osname, execdict['hostcmd']))
        master.write("</pre>\n")
        print("--- AUTO: launched commands for %s" % name)
        for osname, execdict in launched.iteritems():
            print("  %s: waiting for:\n   %s" % (osname, execdict['hostcmd']))
        sys.stdout.flush()

        ssh_results = self._wait_multihost(name=name, launched=launched, tester=tester)
        master.write("<h3>ssh</h3>\n")
        master.write('''<table border="1"><tr>''')
        for osname, ssh_res in ssh_results.iteritems():
            master.write("<td><a href=%s>%s</a></td> " % (ssh_res['ssh_link'], osname))
        master.write("</tr></table>\n")

        all_succeeded = True
        for osname, ssh_res in ssh_results.iteritems():
            loglink = ssh_res['loglink']
            if ssh_res['exit_code'] != 0:
                all_succeeded = False
                master.write("os: %s **FAIL**" % osname)
                print("--- AUTO: **FAIL** %s on %s" % (name,osname))
            else:
                master.write("os: %s **SUCCESS**" % osname)
                print("--- AUTO: **SUCCESS** %s on %s" % (name,osname))
                f = file(os.path.join(self.logDir, "%s-%s.success" % (name,osname)),'w')
                f.close()
            if loglink:
                master.write(" <a href=%s>%s</a>" % (loglink, loglink))
            master.write("<br>\n")
        total_time = time.time()-t0
        minutes = int(total_time//60)
        seconds = int(round(total_time % 60))
        master.write("step time: %d minutes %d seconds<br>" % (minutes, seconds))
        master.close()

        if not all_succeeded:
            self.failureNotify(step=name)
            sys.exit(1)

    def source_tags(self, name):
        cmd = 'ana-rel-admin --cmd psana-conda-src --name %s' % self.version_str
        cmd = self.add_opts(cmd)
        self.execute_step_from_current_host_env(name=name,
                                                cmd=cmd)

    def build_psana(self, name):
        cmd = 'ana-rel-admin --cmd bld-pkg'
        if self.dev:
            cmd += ' --recipe %s/manage/recipes/external/szip' % self.basedir
        else:
            cmd += ' --recipe %s' % util.psanaCondaRecipeDir(self.basedir, self.manageSubDir)
        cmd = self.add_opts(cmd)
        # we want to capture all conda build output to our own file
        cmd += ' --nolog'
        self.execute_multihost_step(name=name,
                                    devel=True,
                                    env='manage',
                                    tester=False,
                                    cmd_or_cmddict=cmd,
                                    html=False)
    
    def _make_envs(self, name, devel):
        clean_cmd = 'ana-rel-admin --cmd rmrel --name %s --force' % self.relName
        self.execute_multihost_step(name="%s_clean" % name,
                                    devel=devel,
                                    env='manage',
                                    tester=False,
                                    cmd_or_cmddict=clean_cmd,
                                    html=False)
        cmd = 'ana-rel-admin --cmd newrel --%s --name %s --nolog' % (self.swGroup, self.relName)
        if self.dev:
            cmd += ' --dev'
        self.execute_multihost_step(name=name,
                                    devel=devel,
                                    env='manage',                                
                                    tester=False,
                                    cmd_or_cmddict=cmd,
                                    html=False)

    def _test_envs(self, name, devel):
        testcmd = os.path.join(self.basedir, 'anarel-test', 'test_conda')
        assert os.path.exists(testcmd), "testcmd %s doesn't exist" % testcmd
        # The tests are different on the OS's.
        # many conda-forge packages aren't supported on rhel5, so the imports/bins/libs may
        # crash. On rhel5, we will only test a few packages we expect to run there.
        # Similarly, some packages may not be installed on rhel6. Right now the 
        # Tensorflow package only runs on rhel7, so we don't install on rhel6. 
        # So for rhel6, use the --soft switch, to not crash if packages are not present,
        # however, for rhel6, explicitly list packages to test so that we crash if 
        # they are not presen.t
        # For rhel7, the most aggressive testing, all imports/bins/libs and pkgs listed in
        # testdb should pass. Note - the list may have to be changed when bins/imports are 
        # removed or renamed in the environments.

        cmddict = {# Turning off tests on rhel5. The psana-conda tests fail because the
                   # ibverbs is not installed correctly on psdev106 and we get warnings about mpi.
                   # not sure why we didn't get them when building psana.
                   # removing conda from the packages tested on rhel6. If we test conda on both rhel6 and rhel7, we
                   # can get locking problems. Even though they are different conda installations,
                   # the conda package tests currently use the same environment in the tester's .conda/envs area,
                   # that is /testing_new_env directory, and so the rhel6 can lock out the rhel7. We could
                   # create environments with os or hostname dependent names.
            
                   #'rhel5':'%s --pkgs --pkglist psana-conda,openmpi,hdf5,mpi4py,h5py,numpy,conda' % testcmd,            
                   'rhel6':'%s --soft --import --bins --libs --pkgs --pkglist psana-conda,openmpi,hdf5,mpi4py,h5py,numpy,scipy,pandas,tables' % testcmd,
                   'rhel7':'%s --verbose --import --bins --libs --pkgs --pkglist all' % testcmd,
               }
#        cmddict = {'rhel7':'which python; %s --verbose --import' % testcmd}
        self.execute_multihost_step(name=name,
                                    devel=devel,
                                    env=self.relName,
                                    tester=True,
                                    cmd_or_cmddict=cmddict,
                                    html=False)

    def dev_envs(self, name):
        self._make_envs(name=name, devel=True)

    def prod_envs(self, name):
        self._make_envs(name=name, devel=False)

    def test_dev_envs(self, name):
        self._test_envs(name, devel=True)

    def test_prod_envs(self, name):
        self._test_envs(name, devel=False)

    def release_notes_variant(self, name, variant, devel, osnames=['rhel5', 'rhel6', 'rhel7']):
        basename = 'ana-current'
        anaRelVariant = self.relName
        if variant:
            assert variant in ['gpu','py3'], "unknown variant=%s, should be 'gpu' or 'py3'" % variant
            basename += '-%s' % variant
            anaRelVariant += '-%s' % variant
            
        anaCurrentFname = os.path.join(self.basedir, 'ana-current', basename)
        assert os.path.exists(anaCurrentFname), "release notes for variant=%s, path: %s doesn't exist" % (variant, anaCurrentFname)
        anaCurrentVariant = file(anaCurrentFname).read().strip()

        cmd = 'ana-rel-admin --cmd env-report --fileA %s --fileB %s' % (anaCurrentVariant, anaRelVariant)
        cmd_dict = {}
        for osname in osnames:
            cmd_dict[osname]=cmd
        self.execute_multihost_step(name=name, 
                                    devel=devel,
                                    env='manage',
                                    tester=False,
                                    cmd_or_cmddict=cmd_dict,
                                    html=True)
        
    def release_notes_py27_prod(self, name):
        self.release_notes_variant(name=name, variant=None, devel=False)

    def release_notes_py27_dev(self, name):
        self.release_notes_variant(name=name, variant=None, devel=True)

    def release_notes_py3_prod(self, name):
        self.release_notes_variant(name=name, variant='py3', devel=False)

    def release_notes_py3_dev(self, name):
        self.release_notes_variant(name=name, variant='py3', devel=True)

    def release_notes_gpu_dev(self, name):
        self.release_notes_variant(name=name, variant='gpu', devel=True, osnames=['rhel7'])

    
def automateReleaseBuildFromArgs(args):
    assert args.name, "must use --name to specify version."
    assert args.ana or args.dm, "must specify one of --ana or --dm"
    assert not (args.ana and args.dm), "can't specify both --ana and --dm"
    
    if args.ana:
        swGroup = 'ana'
    elif args.dm:
        swGroup = 'dm'

    return AutoReleaseBuilder(name=args.name,
                              swGroup=swGroup,
                              basedir=args.basedir,
                              manageSubDir=args.manage,
                              clean=args.clean,
                              tagsfile=args.tagsfile,
                              variant=args.variant,
                              dev=args.dev,
                              email=args.email,
                              force=args.force)
