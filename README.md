[![Build Status](https://travis-ci.org/hexhex/hexlite.svg?branch=master)](https://travis-ci.org/hexhex/hexlite)
[![codebeat badge](https://codebeat.co/badges/5493bd59-f87f-470c-9069-86d4c14dd374)](https://codebeat.co/projects/github-com-hexhex-hexlite-master)
[![Anaconda-Server Badge](https://anaconda.org/peterschueller/hexlite/badges/installer/conda.svg)](https://conda.anaconda.org/peterschueller)

# Hexlite - Solver for a fragment of HEX

This is a solver for a fragment of the HEX language and for Python-based plugins
which is based on Python interfaces of Clingo and does not contain any C++ code itself.

The intention is to provide a lightweight system for an easy start with HEX.

The vision is that HEXLite can use existing Python plugins and runs based on
the Clingo python interface, without realizing the full power of HEX.

The system is currently under development and only works for certain programs:
* External atoms with only constant inputs are evaluated during grounding in Gringo
* External atoms with predicate input(s) and no constant outputs are evaluated during solving in a clasp Propagator
* External atoms with predicate input(s) and constant outputs that have a domain predicate can also be evaluated
* Liberal Safety is not implemented
* Properties of external atoms are not used
* If it has a finite grounding, it will terminate, otherwise, it will not - as usual with Gringo
* FLP Check is implemented explicitly and does not work with strong negation and weak constraints
* FLP Check can be deactivated
* There is a Java Plugin API (see below)

The system is described in the following publication.

  Peter Schüller (2019)
  The Hexlite Solver.
  In: Logics in Artificial Intelligence. JELIA 2019. Lecture Notes in Computer Science, vol 11468. Springer, Cham
  https://doi.org/10.1007/978-3-030-19570-0_39

In case of bugs please report an issue here: https://github.com/hexhex/hexlite/issues

* License: MIT
* Author: Peter Schüller <schueller.p@gmail.com>
* Available at PyPi: https://pypi.python.org/pypi/hexlite
* Installation with Conda:

  The easiest way to install `hexlite` is Conda.
  
  ```$ conda install -c peterschueller -c potassco -c conda-forge hexlite```

  (We need the `potassco` channel for `clingo` and the `conda-forge` channel for `jpype1`.)

  Then you test hexlite:

  ```$ hexlite -h```

* Installation with pip:

  This will download, build, and locally install Python-enabled `clingo` modules.

  * If you do not have it: install `python-pip`: for example under Ubuntu via
    
    ```$ sudo apt-get install python-pip```

  * Install hexlite:

    ```$ pip install hexlite --user```

  * Setup Python to use the "Userinstall" environment that allows you
    to install Python programs without overwriting system packages:

    Add the following to your `.profile` or `.bashrc` file:

    ```
    export PYTHONUSERBASE=~/.local/
    export PATH=$PATH:~/.local/bin
    ```

  * Run hexlite the first time.

    ```$ hexlite```

    The first run of hexlite might ask you to enter the sudo password
    to install several packages.
    (You can do this manually. Simply abort and later run `hexlite` again.)

  * Ubuntu 16.04 is tested
  * Debian 8.6 (jessie) is tested
  * Ubuntu 14.04 can not work without manual installation of cmake 3.1 or higher (for buildling clingo)

* Using the Java API

  Building the JAVA API is not automated, you need to install `maven` and run

  ```mvn clean compile package install```

  See also `.travis.yml` how to build and install and test the Java plugin.

* Using the Docker image

  There is a Dockerfile that builds a docker image where hexlite and its source code is installed.

  Build the image with

  ```$ ./build-docker-image.sh```

  Run the image and start a shell in the image with

  ```$ ./run-docker-image.sh```
  
  In the image, run an example:

  ```
  # hexlite --pluginpath /opt/hexlite/plugins/ --plugin testplugin -- /opt/hexlite/tests/inputs/extatom2.hex
  ```

  Should give the following output (it is a set, the order of items does not matter):

  `{prefix("test:"),more("a","b","c"),complete("test: a b c")}`

# Running Hexlite on Examples in the Repository

* If `hexlite` by itself shows the help, you can run it on some examples in the repository.

* Hexlite needs to know where to find plugins and what is the name of the Python modules of these plugins

	* The path for plugins is given as argument ``--pluginpath <path>``.

	  This argument can be given multiple times. You can use absolute or relative paths.

	* The python modules to load are given as argument ``--plugin <module> [<argument1> <argument2>]``.
	
	  Multiple plugins can be loaded.
          Each plugin can have arguments.

	  !ATTENTION!:
	  If you specify the HEX input file after ``--plugin <module>``, it becomes the argument of the plugin.
	  In this case, you need to
	
	  * specify the HEX input files _before_ the other arguments
	  or
	  * indicate end of the argument list with the ``--`` option.

* To run one of the examples in the ``tests/`` directory you can use one of the following methods to call hexlite:

  ```
  $ hexlite --pluginpath ./plugins/ --plugin testplugin -- tests/inputs/extatom3.hex
  $ hexlite tests/inputs/extatom3.hex --pluginpath ./plugins/ --plugin testplugin
  $ hexlite --pluginpath=./plugins/ --plugin=testplugin tests/inputs/extatom3.hex
  ```

# Developer Readme

* For developing hexlite without uploading to anaconda repository:

  * Install clingo with conda or pip, but but do **not** install hexlite with conda.

    ```$ conda install -c potassco clingo```

    or

    ```$ pip install clingo```

  * checkout hexlite with git

    ```$ git clone git@github.com:hexhex/hexlite.git```

  * install `hexlite` in develop mode into your user-defined Python space:

    ```$ python3 setup.py develop --user```

  * If you want to remove this development installation:

    ```
    $ python3 setup.py develop --uninstall --user
    $ rm ~/.local/bin/hexlite
    ```

  (Installed scripts are not automatically uninstalled.)

* Releasing

  For building and uploading a new version to pip and conda (Note: conda requires to upload to pip first)
  
  * Update version in `setup.py`.

  * Build pypi source package

    `$ python setup.py sdist`

	* Verify that dist/ contains the right archives with the right content (no wheels etc.)

	* Upload to pypi (the twine in Ubuntu 18.04 does not work, you must install via `pip3 install twine`)

    `$ twine upload dist/*`

  * Update version in `meta.yaml`.

  * Build for anaconda cloud
  
    First, some conda packages need to be installed via `conda install conda-build conda-verify anaconda`.

    `$ conda build . -c potassco`
    
    or
    
    `$ conda build . -c potassco --no-verify --no-test`

    (get upload command from last lines of output, check output, then re-run without the last two arguments.)

    If conda is installed on an encrypted /home/ or similar, this will abort with a permission error.
    You can make it work by creating a new directory on an unencrypted `/tmp/`, for example `/tmp/conda-build`,
    and run conda build as follows:

    `$ conda build --croot /tmp/conda-build/ .  -c potassco`

  * Verify that archive to upload contains the right content (and no backup files, experimental results, etc...)

    `$ anaconda upload <path-from-conda-build>`

