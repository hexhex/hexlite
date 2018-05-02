WHAT="./tests/not_some_selected_partial.hex"
EXTRA=""
#EXTRA="$EXTRA --debug"
#EXTRA="$EXTRA --verbose"
hexlite $EXTRA \
  --pluginpath=./plugins/ \
  --plugin=stringplugin --plugin=testplugin \
  $WHAT 
  
