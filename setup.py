#!/usr/bin/env python3

import sys
import platform
import setuptools

if platform.python_version().startswith('2'):
  sys.stdout.write("Please use Python 3 instead of Python 2!\n")
  sys.exit(-1)

def readme():
  with open('README', 'wb') as of:
    with open('README.md', 'rb') as i:
      out = b''.join([ line for line in i if not line.startswith(b'[')])
      of.write(out)
      return out.decode('utf8')

setuptools.setup(name='hexlite',
      version='0.3.16',
      description='HEXLite Python-based solver for a fragment of HEX',
      long_description=readme(),
      classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Utilities',
      ],
      url='https://github.com/hexhex/hexlite',
      author='Peter Schuller',
      author_email='schueller.p@gmail.com',
      license='GPL3',
      packages=['hexlite', 'hexlite.ast', 'dlvhex'],
      install_requires=[
        'ply',
      ],
      scripts=['bin/hexlite'],
      zip_safe=False)
