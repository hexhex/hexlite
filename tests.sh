#!/usr/bin/env bash

WHAT="./tests/extatom2.hex"
for WHAT in ./tests/simple{1,2}.hex ./tests/percentparser.hex; do
  echo "=== $WHAT"
  EXTRA=""
  hexlite $EXTRA \
    --pluginpath=./plugins/ \
    --plugin=stringplugin --plugin=testplugin \
    $WHAT
done

# for acthex development
if /bin/false; then
  echo "+++++"

  WHAT="./tests/acthex_bubblesort_sortenv.hex"
  EXTRA="--plugin=stringplugin"
  EXTRA=""
  EXTRA="$EXTRA --debug"
  EXTRA="$EXTRA --verbose"
  acthex $EXTRA \
    --pluginpath=./plugins/ \
    --plugin=acthex-testplugin \
    $WHAT

  echo "====="

  WHAT="./tests/acthex_bubblesort_persistenceenv.hex"
  EXTRA="--plugin=stringplugin"
  EXTRA=""
  EXTRA="$EXTRA --debug"
  EXTRA="$EXTRA --verbose"
  acthex $EXTRA \
    --pluginpath=./plugins/ \
    --plugin=acthex-testplugin \
    $WHAT
    
fi
