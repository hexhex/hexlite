#!/usr/bin/env python2

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

import os, sys, subprocess, logging

class Installer:
  ARCHIVE = 'v5.2.0.tar.gz'
  URL = 'https://github.com/potassco/clingo/archive/'+ARCHIVE
  DIR_IN_ARCHIVE = 'clingo-5.2.0'
  UNPACKDIR = '/tmp/hexlite-install-clingo/'
  INSTALLDIR = os.path.expanduser('~/.hexlite/')
  SRCDIR = UNPACKDIR+DIR_IN_ARCHIVE
  # you can change this to reduce/increase number of parallel jobs
  MAKEARGS = ['VERBOSE=1', '--jobs=4']

  def run_cmd(self, cmd, **args):
    logging.info("running command '{}'".format(cmd))
    subprocess.check_call(cmd, **args)

  def prompt_user(self, message):
    print message
    answer = None
    while answer not in ['n', 'y', 's']:
      print "Continue? (y/n/s) (yes, no, skip)"
      answer = sys.stdin.readline().strip()
    if answer == 'n':
      raise Exception("User aborted setup")
    if answer == 'y':
      return True
    # skip
    return False

  def makedirs(self):
    prompt = "Will next create directories {} for installation".format(repr([self.UNPACKDIR, self.INSTALLDIR]))
    if not self.prompt_user(prompt):
      return
    for d in [self.UNPACKDIR, self.INSTALLDIR]:
      try:
        os.makedirs(d)
      except:
        logging.critical('could not create directory '+d)

  def download(self):
    prompt = "Will next dowload " + self.URL
    if not self.prompt_user(prompt):
      return
    self.run_cmd(['wget', self.URL, '--output-document='+self.UNPACKDIR+self.ARCHIVE])

  def unpack(self):
    prompt = "Will next unpack downloaded archive to " + self.UNPACKDIR
    if not self.prompt_user(prompt):
      return
    self.run_cmd(['tar', 'xzf', self.ARCHIVE], cwd=self.UNPACKDIR)

  def build(self):
    prompt = "Will next run cmake"
    if self.prompt_user(prompt):
      cmd = [
        'cmake', '.', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX='+self.INSTALLDIR,
        '-DCLINGO_BUILD_PY_SHARED=ON', '-DPYCLINGO_INSTALL_DIR='+self.INSTALLDIR]
      self.run_cmd(cmd, cwd=self.SRCDIR)
    prompt = "Will next run make with arguments MAKEARGS={}".format(repr(self.MAKEARGS))
    if self.prompt_user(prompt):
      self.run_cmd(['make']+self.MAKEARGS, cwd=self.SRCDIR)

  def install(self):
    self.run_cmd(['make', 'install'], cwd=self.SRCDIR)

  def doit(self):
    self.makedirs()
    self.download()
    self.unpack()
    self.build()
    self.install()

def build():
  try:
    lsbout = subprocess.check_output(['lsb_release', '-d'])
    #logging.debug('got LSB output '+lsbout)
    if 'Ubuntu 16.04' in lsbout:
      logging.info('installing for Ubuntu 16.04')
      inst = Installer()
      inst.doit()
    elif 'Ubuntu' in lsbout:
      logging.warning('installing for nonsupported Ubuntu')
      inst = Installer()
      inst.doit()
    else:
      logging.critical("We are sorry, your operating system seems to be unsupported."+
        " Please contact the developers and provide this information: '"+lsbout+"'")
      return False
  except IOError:
    logging.critical("We are sorry, could not determine your operating system." +
      " Please contact the developers.")
    return False
  return True
