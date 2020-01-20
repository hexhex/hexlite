#!/usr/bin/env bash

# generic

if /bin/true; then
  for WHAT in ./tests/extatom2.hex; do
    echo "=== $WHAT"
    EXTRA="--verbose"
    EXTRA=""
    hexlite $EXTRA \
      --pluginpath=./plugins/ \
      --plugin=stringplugin --plugin=testplugin \
      $WHAT
  done
fi

# for java plugin
if /bin/true; then
  for WHAT in ./tests/extatom2.hex; do
    echo "=== $WHAT"
    pushd java-api ; mvn compile ; popd
    EXTRA="--verbose --debug"
    EXTRA=""
    CLASSPATH=./java-api/target/classes \
    hexlite --pluginpath=./plugins/ \
      --plugin javaapiplugin at.ac.tuwien.kr.hexlite.testplugin.ConcatSetMinusPlugin \
      $EXTRA \
      -- $WHAT
  done
fi

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
