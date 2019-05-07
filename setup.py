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

readme_txt = readme()
setuptools.setup(name='hexlite',
      version='1.0.1',
      description='Hexlite - Solver for a fragment of HEX',
      long_description=readme_txt,
      classifiers=[
        'Development Status :: 5 - Production/Stable',
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
      author='Peter Schueller',
      author_email='schueller.p@gmail.com',
      license='GPL3',
      packages=['hexlite', 'hexlite.ast', 'dlvhex', 'acthex'],
      install_requires=[
        'ply',
      ],
      scripts=['bin/hexlite', 'bin/acthex'],
      zip_safe=False)
