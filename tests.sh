#!/usr/bin/env bash

# rebuild java plugin
#pushd java-api ; mvn compile ; popd

# generic

if /bin/true; then
  # ./tests/inputs/extatom2.hex
  # ./tests/inputs/extatom10.hex;
  # ./tests/inputs/store_parseable_1.hex
  # ./tests/inputs/setminus_learn1.hex 
  # ./tests/inputs/setminus_learn2.hex
  for WHAT in ./tests/inputs/relevance_learning2.hex; do
    echo "=== $WHAT python"
    EXTRA=""
    EXTRA="--verbose"
    EXTRA="--verbose --debug"
    EXTRA="--verbose --debug --flpcheck=none --stats"
    EXTRA="--verbose --debug --flpcheck=none --stats --noskipevalfromnogoods"
    EXTRA="--verbose --debug --flpcheck=none --stats --nocache"
    EXTRA="--stats --nocache"
    hexlite $EXTRA \
      --pluginpath=./plugins/ \
      --plugin=stringplugin --plugin=testplugin \
      $WHAT
  done
fi

# for java plugin
if /bin/false; then
  # ./tests/inputs/extatom2.hex 
  # ./tests/inputs/extatom10.hex
  # ./tests/inputs/nonmon_guess.hex
  # ./tests/inputs/setminus_learn.hex
  PLUGIN=at.ac.tuwien.kr.hexlite.testplugin.SetMinusApi2Plugin
  PLUGIN=at.ac.tuwien.kr.hexlite.testplugin.SetMinusApi3Plugin
  PLUGIN=at.ac.tuwien.kr.hexlite.testplugin.ConcatSetMinusPlugin
  for WHAT in ./tests/inputs/nonmon_guess.hex ./tests/inputs/nonmon_inc.hex ./tests/inputs/nonmon_guess.hex ./tests/inputs/nonmon_inc.hex ; do
    echo "=== $WHAT java"
    EXTRA="--verbose --debug"
    EXTRA="--verbose"
    EXTRA=""
    CLASSPATH=./java-api/target/classes \
    hexlite --pluginpath=./plugins/ \
      --plugin javaapiplugin $PLUGIN \
      $EXTRA \
      -- $WHAT
  done
fi

# for acthex development
if /bin/false; then
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
