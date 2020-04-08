#!/usr/bin/env bash

WHAT="./tests/inputs/extatom2.hex"
for WHAT in ./tests/inputs/simple{1,2}.hex ./tests/inputs/percentparser.hex; do
  echo "=== $WHAT"
  EXTRA=""
  hexlite $EXTRA \
    --pluginpath=./plugins/ \
    --plugin=stringplugin --plugin=testplugin \
    $WHAT
done

# for acthex development
if /bin/true; then
  echo "+++++"

  WHAT="./tests/inputs/acthex_bubblesort_sortenv.hex"
  EXTRA="--plugin=stringplugin"
  EXTRA=""
  EXTRA="$EXTRA --debug"
  EXTRA="$EXTRA --verbose"
  acthex $EXTRA \
    --pluginpath=./plugins/ \
    --plugin=acthex-testplugin \
    $WHAT

  echo "====="

  WHAT="./tests/inputs/acthex_bubblesort_persistenceenv.hex"
  EXTRA="--plugin=stringplugin"
  EXTRA=""
  EXTRA="$EXTRA --debug"
  EXTRA="$EXTRA --verbose"
  acthex $EXTRA \
    --pluginpath=./plugins/ \
    --plugin=acthex-testplugin \
    $WHAT
    
fi
