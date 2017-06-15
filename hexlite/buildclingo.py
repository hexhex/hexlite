# HEXLite Python-based solver for a fragment of HEX
# Copyright (C) 2017  Peter Schueller <schueller.p@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# this module supports building clingo module from the distribution

import os, sys, subprocess, logging, tempfile, traceback

def msg(m):
  sys.stderr.write(m+'\n')

class InstallerBase:
  # you can change this to reduce/increase number of parallel jobs
  MAKEARGS = ['VERBOSE=1', '--jobs=4']

  def __init__(self):
    self.allyes = False
    self.tmpdir = None
    self.INSTALLDIR = os.path.expanduser('~/.hexlite/')

  def run_cmd(self, cmd, **args):
    logging.info("running command '{}'".format(' '.join(cmd)))
    subprocess.check_call(cmd, **args)

  def prompt_user(self, message):
    msg(message)
    if self.allyes:
      return True
    answer = None
    while answer not in ['n', 'y', 's', 'a']:
      msg("Continue? (y/n/s/a) (yes, no, skip one, all yes)")
      answer = sys.stdin.readline().strip()
    if answer == 'n':
      raise Exception("User aborted setup")
    if answer == 'a':
      self.allyes = True
    if answer in ['y','a']:
      return True
    # skip
    return False

  def ensurepackages(self, packages):
    cmd = ['dpkg-query', '-W', "-f=${Package}\\n"]
    logging.info('obtaining list of installed packages with command '+repr(cmd))
    allpackages = subprocess.check_output(cmd).decode('utf8')
    logging.info('got list '+repr(allpackages))
    allpackages = set([pkg.strip() for pkg in allpackages.split('\n')])
    need = [pkg for pkg in packages if pkg not in allpackages]
    if len(need) > 0:
      logging.info("did not find required packages {} via dpkg".format(repr(need)))
      prompt = "Will run 'sudo apt-get install {}' (you may do this yourself and restart this script, no other installation part requires sudo)".format(repr(need))
      if not self.prompt_user(prompt):
        return
      subprocess.check_call(['sudo', 'apt-get', 'install']+list(need))

  def maketargetdir(self):
    d = self.INSTALLDIR
    if not os.path.isdir(d):
      try:
        prompt = "Will create directory {} for installation".format(d)
        if not self.prompt_user(prompt):
          return
        os.makedirs(d)
      except:
        raise Exception('could not create output directory '+d)

  def prepare(self, packages):
    self.ensurepackages(packages)
    self.maketargetdir()
    self.tmpdir = tempfile.TemporaryDirectory()

  def build_install(self, srcdir):
    cmd = [
      'cmake', '.', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX='+self.INSTALLDIR,
      '-DCLINGO_BUILD_PY_SHARED=ON', '-DPYCLINGO_INSTALL_DIR='+self.INSTALLDIR,
      '-DPYTHON_EXECUTABLE=/usr/bin/python3']
    prompt = "Will next run cmake in {} with command {}".format(srcdir, repr(cmd))
    if self.prompt_user(prompt):
      self.run_cmd(cmd, cwd=srcdir)
    prompt = "Will next run make and make install with arguments MAKEARGS={}".format(repr(self.MAKEARGS))
    if self.prompt_user(prompt):
      self.run_cmd(['make']+self.MAKEARGS, cwd=srcdir)
      self.run_cmd(['make', 'install'], cwd=srcdir)
      logging.info("removing temporary directory")
      self.tmpdir.cleanup()

class ArchivedReleaseInstaller(InstallerBase):
  ARCHIVE = 'v5.2.0.tar.gz'
  URL = 'https://github.com/potassco/clingo/archive/'+ARCHIVE
  DIR_IN_ARCHIVE = 'clingo-5.2.0'

  def __init__(self):
    InstallerBase.__init__(self)

  def download(self):
    logging.info("Dowloading " + self.URL)
    self.run_cmd(['wget', self.URL, '--output-document='+os.path.join(self.tmpdir.name, self.ARCHIVE)])

  def unpack(self):
    logging.info("Unpacking downloaded archive to " + self.tmpdir.name)
    self.run_cmd(['tar', 'xzf', self.ARCHIVE], cwd=self.tmpdir.name)
    self.SRCDIR = os.path.join(self.tmpdir.name, self.DIR_IN_ARCHIVE)

  def doit(self, packages):
    self.prepare(packages)
    self.download()
    self.unpack()
    self.build_install(self.SRCDIR)

class GitCheckoutInstaller(InstallerBase):
  GITURL = 'https://github.com/potassco/clingo.git'
  VERSION = '01dffb'

  def __init__(self):
    InstallerBase.__init__(self)

  def clone(self):
    logging.info("Cloning {} into {}".format(self.GITURL, self.tmpdir.name))
    self.run_cmd(['git', 'clone', '--recursive', self.GITURL, os.path.join(self.tmpdir.name)])

  def checkout(self):
    logging.info("Checking out {}".format(self.VERSION))
    self.run_cmd(['git', 'checkout', self.VERSION], cwd=self.tmpdir.name)
    self.run_cmd(['git', 'submodule', 'update', '--recursive'], cwd=self.tmpdir.name)

  def doit(self, packages):
    self.prepare(packages)
    self.clone()
    self.checkout()
    self.build_install(self.tmpdir.name)

def build():
  try:
    lsbid = subprocess.check_output(['lsb_release', '--short', '--id']).decode('utf8').strip()
    lsbrelease = subprocess.check_output(['lsb_release', '--short', '--release']).decode('utf8').strip()
    logging.debug('got LSB id {} and release {}'.format(lsbid, lsbrelease))
    # for installing from release packages
    #USUALPACKAGES = ['wget', 'tar', 'gzip', 'cmake', 'g++', 'libpython3-dev']
    # for installing from git
    USUALPACKAGES = ['wget', 'tar', 'gzip', 'cmake', 'g++', 'libpython3-dev', 'bison', 're2c', 'git']
    IMPOSSIBLE = {
      ('Ubuntu', '14.04'): 'Does not contain sufficiently new cmake and g++ for automatic build (you can try to manually install these)'
    }
    UBUNTU_TESTED = ['16.04', '16.10', '17.04']
    DEBIAN_TESTED = ['?']
    inst = ArchivedReleaseInstaller()
    inst = GitCheckoutInstaller()
    if lsbid == 'Ubuntu':
      if lsbrelease == '14.04':
        raise Exception("Ubuntu 14.04 does not contain modern cmake required for building clingo")
      elif lsbrelease in UBUNTU_TESTED:
        logging.info('installing for tested Ubuntu version')
        inst.doit(USUALPACKAGES)
      else:
        logging.info('installing for untested Ubuntu version {} (tested = {})'.format(lsbrelease, repr(UBUNTU_TESTED)))
        inst.doit(USUALPACKAGES)
    elif lsbid == 'Debian':
      if lsbrelease in DEBIAN_TESTED:
        logging.info('installing for tested Debian version')
        inst.doit(USUALPACKAGES)
      else:
        logging.info('installing for untested Debian version {} (tested = {})'.format(lsbrelease, repr(DEBIAN_TESTED)))
        inst.doit(USUALPACKAGES)
    else:
      logging.info('installing for untested Linux id {} and release {} (tested = Ubuntu {} and Debian {})'.format(
        repr(lsbid), repr(lsbrelease),
        repr(UBUNTU_TESTED), repr(DEBIAN_TESTED)))
      inst.doit(USUALPACKAGES)
  except IOError:
    logging.critical("We are sorry, could not determine your operating system." +
      " Please contact the developers.")
    return False
  except:
    logging.critical("Unexpected Exception:"+traceback.format_exc()+"\nPlease contact the developers.")
    return False
  return True
