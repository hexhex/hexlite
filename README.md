[![Build Status](https://travis-ci.org/hexhex/hexlite.svg?branch=master)](https://travis-ci.org/hexhex/hexlite)
[![codebeat badge](https://codebeat.co/badges/5493bd59-f87f-470c-9069-86d4c14dd374)](https://codebeat.co/projects/github-com-hexhex-hexlite-master)

# HEXLite Python-based solver for a fragment of HEX

This is a solver for a fragment of the HEX language and for Python-based plugins
which is based on Python interfaces of Clingo and WASP and does not contain any
C++ code itself.

The intention is to provide a lightweight system for an easy start with HEX.

The vision is that HEXLite can use existing Python plugins and runs based on
the Clingo or WASP python interface, without realizing the full power of HEX.

The system is currently under development and only works for certain programs:
* External atoms with only constant inputs are evaluated during grounding in Gringo
* External atoms with predicate input(s) and no constant outputs are evaluated during solving in a clasp Propagator
* External atoms with predicate input(s) and constant outputs that have a domain predicate can also be evaluated
* Liberal Safety is not implemented
* Properties of external atoms are not used
* If it has a finite grounding, it will terminate, otherwise, it will not - as usual with Gringo
* FLP Check is implemented explicitly and does not work with strong negation and weak constraints
* FLP Check can be deactivated

A manuscript about the system is under preparation.

In case of bugs please report an issue here: https://github.com/hexhex/hexlite/issues

* License: GPL (3.0)
* Author: Peter Schüller <schueller.p@gmail.com>
* Available at PyPi: https://pypi.python.org/pypi/hexlite
* Installation: ```sudo pip install hexlite```
  (You might need to install python-pip under Ubuntu ```sudo apt-get install python-pip```.)
  Ubuntu 16.04 works
  Debian 8.6 (jessie) works
  Ubuntu 14.04 does not work automatically (CMake 3.1 or higher is required by clingo)
