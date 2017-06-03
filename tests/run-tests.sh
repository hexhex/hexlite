#!/bin/bash

DLVHEX="python2 ../bin/hexlite --pluginpath=../plugins/ --plugin=testplugin"
EXAMPLESDIR="./"
OUTDIR="./outputs/"
TESTS="suites/complete.test"

#
# brief documentation of this script
#
# relevant environment variables:
# TOP_SRCDIR (as in automake)
# DLVHEX (binary to use as dlvhex, may include commandline parameters)
# EXAMPLESDIR (directory where hex input files are located)
# TESTDIR (deprecated, directory where .test files are located)
# TESTS (.test files to use)
# OUTDIR (directory where .out/.stdout/.stderr files are located)
#
# this script looks for files called "*.test" in $TESTDIR
# each line in such a file is parsed:
# * first word is location of input hex file (relative to $TESTDIR)
# * second word is the filename of an existing file (relative to $TESTDIR)
#   * if the extension is ".out" this is a positive testcase
#     the file contains lines of answer sets
#     successful termination of dlvhex is expected
#   * if the extension is ".stderr" this is a special error testcase
#     the file contains one line:
#     * the first word is an integer (verifying the return value of dlvhex)
#     * the remaining line is a command executed with the error output
#       if this execution succeeds (= returns 0) the test is successful
#       e.g.: [grep -q "rule.* is not strongly safe"] (without square brackets)
#   * if the extension is ".stdout" this is a special output testcase
#     (procedure as with ".stderr" only that standard output is verified
# * the rest of the input line are parameters used for executing dlvhex
#   e.g.: [--nofact -ra] (without square brackets)
#

#
# HexLite
# Copyright (C) 2017 Peter Schüller
#
# adapted from dlvhex -- Answer-Set Programming with external interfaces.
# Copyright (C) 2005, 2006, 2007 Roman Schindlauer
# Copyright (C) 2006, 2007, 2008, 2009, 2010 Thomas Krennwallner
# Copyright (C) 2009, 2010 Peter Schüller
#
# dlvhex is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of the
# License, or (at your option) any later version.
#
# dlvhex is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with dlvhex; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
# USA.
#

test "x${DLVHEX}" != "x" || { echo "need DLVHEX variable to be set!"; exit -1; }
test "x${EXAMPLESDIR}" != "x" || { echo "need EXAMPLESDIR variable to be set!"; exit -1; }
test "x${OUTDIR}" != "x" || { echo "need OUTDIR variable to be set!"; exit -1; }
test "x${TESTS}" != "x" || { echo "need TESTS variable to be set!"; exit -1; }
ANSWERSETCOMPARE=./answerset_compare.py

MKTEMP="mktemp -t tmp.XXXXXXXXXX"
TMPFILE=$($MKTEMP) # global temp. file for answer sets
ETMPFILE=$($MKTEMP) # global temp. file for errors

passed=0
failed=0
warned=0
ntests=0

echo "============ dlvhex tests start ============"
echo "(executing in directory " $(pwd) ")"
echo "DLVHEX=${DLVHEX/!/\\!}"

for t in ${TESTS};
do
  # "read" assigns first word to first variable,
  # second word to second variable,
  # and all remaining words to the last variable
  while read HEXPROGRAM VERIFICATIONFILE ADDPARM
  do
    # skip comment lines
    COMMENTMARKER=${HEXPROGRAM:0:1}
    if test x"${COMMENTMARKER}" == x"#"; then
      continue
    fi

    let ntests++

    # check if we have the input file
    if test ${HEXPROGRAM:0:1} != "/"; then
        HEXPROGRAM=$EXAMPLESDIR/$HEXPROGRAM
    fi
    if [ ! -f $HEXPROGRAM ]; then
        echo FAIL: Could not find program file $HEXPROGRAM
        let failed++
        continue
    fi

    VERIFICATIONEXT=${VERIFICATIONFILE: -7}
    #echo "verificationext = ${VERIFICATIONEXT}"
    if test "x$VERIFICATIONEXT" == "x.stderr" -o "x$VERIFICATIONEXT" == "x.stdout"; then
      #echo "negative testcase"

      if test ${VERIFICATIONFILE:0:1} == "/"; then
          ERRORFILE=$VERIFICATIONFILE
      else
          ERRORFILE=$OUTDIR/$VERIFICATIONFILE
      fi
      if [ ! -f $ERRORFILE ]; then
          echo "FAIL: $HEXPROGRAM: could not find verification file $ERRORFILE"
          let failed++
          continue
      fi

      # run dlvhex with specified parameters and program
      $DLVHEX $ADDPARM $HEXPROGRAM 2>$ETMPFILE >$TMPFILE
      RETVAL=$?
      #set -x
      #set -v
      # check error code and output
      read VRETVAL VCOMMAND <$ERRORFILE
      if test "x$VRETVAL" == "x" -o "x$VCOMMAND" == "x"; then
          echo "FAIL: $HEXPROGRAM: could not read VRETVAL from verification file $ERRORFILE"
          let failed++
          continue
      fi
      #echo "verifying return value '$RETVAL'"
      if [ $VRETVAL -eq $RETVAL ]; then
        #echo "verifying with command '$VCOMMAND'"
        # select output to check
        if test "x$VERIFICATIONEXT" == "x.stderr"; then
          VTMPFILE=$ETMPFILE
        else
          VTMPFILE=$TMPFILE
        fi
        # check output
        if bash -c "cat $VTMPFILE |$VCOMMAND"; then
          echo "PASS: $HEXPROGRAM $ADDPARM (special testcase)"
          let passed++
        else
          echo "FAIL: ${DLVHEX/!/\\!} $ADDPARM $HEXPROGRAM (output not verified by $VCOMMAND)"
          cat $VTMPFILE
          let failed++
        fi
      else
        echo "FAIL: ${DLVHEX/!/\\!} $ADDPARM $HEXPROGRAM (return value $RETVAL not equal reference value $VRETVAL)"
        cat $ETMPFILE
        let failed++
      fi
      #set +x
      #set +v
    else
      VERIFICATIONEXT=${VERIFICATIONFILE: -4}
      if test "x$VERIFICATIONEXT" == "x.out"; then
        #echo "model-verifying testcase"
        
        if test ${VERIFICATIONFILE:0:1} == "/"; then
            ANSWERSETSFILE=$VERIFICATIONFILE
        else
            ANSWERSETSFILE=$OUTDIR/$VERIFICATIONFILE
        fi
        if [ ! -f $ANSWERSETSFILE ]; then
            echo "FAIL: $HEXPROGRAM: could not find answer set file $ANSWERSETSFILE"
            let failed++
            continue
        fi

        # run dlvhex with specified parameters and program
        $DLVHEX $ADDPARM $HEXPROGRAM >$TMPFILE
        RETVAL=$?
        if [ $RETVAL -eq 0 ]; then
          if $ANSWERSETCOMPARE $TMPFILE $ANSWERSETSFILE; then
              echo "PASS: $HEXPROGRAM $ADDPARM"
              let passed++
          else
              echo "FAIL: ${DLVHEX/!/\\!} $ADDPARM $HEXPROGRAM (answersets differ)"
              let failed++
          fi
        else
          echo "FAIL: ${DLVHEX/!/\\!} $ADDPARM $HEXPROGRAM (abnormal termination)"
          let failed++
        fi
      else
        echo "FAIL: ${DLVHEX/!/\\!} $ADDPARM $HEXPROGRAM: type of testcase must be '.out', '.stdout', or '.stderr', got '$VERIFICATIONEXT'"
        let failed++
        continue
      fi
    fi

  done < $t # redirect test file to the while loop
done

# cleanup
rm -f $TMPFILE
rm -f $ETMPFILE

echo ========== dlvhex tests completed ==========

echo Time: $SECONDS seconds
echo Tested $ntests dlvhex programs
echo $failed failed tests, $warned warnings, $passed passed tests

echo ============= dlvhex tests end =============

exit $failed
