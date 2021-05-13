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
            out = b''.join([line for line in i if not line.startswith(b'[')])
            of.write(out)
            return out.decode('utf8')


readme_txt = readme()
setuptools.setup(
    name='hexlite',
    version='1.4.0',
    description='Hexlite - Solver for a fragment of HEX',
    long_description=readme_txt,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3',
        'Programming Language :: Java',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Utilities',
    ],
    url='https://github.com/hexhex/hexlite',
    author='Peter Schueller',
    author_email='schueller.p@gmail.com',
    license='MIT License',
    packages=['hexlite', 'hexlite.ast', 'dlvhex', 'acthex'],
    install_requires=[
        'ply>=3.11',
        'clingo>=5.5.0',
        'jpype1>=1.2.1'
    ],
    entry_points={
        'console_scripts': [
            'hexlite=hexlite.main:main',
            'acthex=acthex.main:main',
        ],
    },
    zip_safe=False)
