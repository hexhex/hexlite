#!/usr/bin/env python3

import sys
import json
import logging
import traceback

# reads input from stdin
# interprets each line as json
# interprets each commandline argument as python datastructure (with eval)
# verifies if the json lines are equal to the commandline arguments

def setlike_compare(a,b):
  logging.debug("a %s", a)
  logging.debug("b %s", b)
  if a['cost'] != b['cost']:
    return False

  if set(a['stratoms']) != set(b['stratoms']):
    return False

  # this is inefficient but it works
  for x in a['atoms']:
    if x not in b['atoms']:
      return False

  for x in b['atoms']:
    if x not in a['atoms']:
      return False

  return True

def main():
  # load from arguments
  desired = [ eval(x) for x in sys.argv[1:] ]
  logging.debug('desired %s', desired)

  # load from stdin
  obtained = [ l for l in sys.stdin.read().split('\n') ]
  logging.debug('obtained %s', obtained)
  jsonobtained = []
  for idx, l in enumerate(obtained):
    if l.strip() == '':
      continue
    try:
      j = json.loads(l)
      jsonobtained.append(j)
    except:
      logging.warning("could not interpret line %d of input as json: %s", idx, l)
      logging.warning("exception: %s", traceback.format_exc())
  logging.debug('jsonobtained %s', jsonobtained)

  # compare (tricky because we have to compare some parts of the JSON as sets, and JSON does not support sets
  d_found = set()
  d_missing = set()
  o_covered = set()
  for di, d in enumerate(desired):
    found = False
    for oi, o in enumerate(jsonobtained):
      if setlike_compare(d,o):
        found = True
        d_found.add(di)
        o_covered.add(oi)
        break
    if not found:
      d_missing.add(di)

  if len(o_covered) == len(desired) and len(d_missing) == 0:
    # input = expected output
    sys.exit(0)
  else:
    # input != expected output
    for mi in d_missing:
      logging.warning("missing in obtained output: %s", desired[mi])
    for oi, o in enumerate(jsonobtained):
      if oi not in o_covered:
        logging.warning("superfluous in obtained output: %s", o)
    sys.exit(1)

main()
