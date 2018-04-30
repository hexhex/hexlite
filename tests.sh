WHAT="./tests/partialTest.hex"
WHAT="./tests/setminus.hex"
WHAT="./tests/setminus_learn.hex"
EXTRA=""
EXTRA="$EXTRA --debug"
hexlite $EXTRA \
  --pluginpath=./plugins/ \
  --plugin=stringplugin --plugin=testplugin \
  $WHAT 
  
