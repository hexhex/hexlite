WHAT="./tests/acthex_bubblesort_sortenv.hex"
EXTRA="--plugin=stringplugin"
EXTRA=""
#EXTRA="$EXTRA --debug"
#EXTRA="$EXTRA --verbose"
acthex $EXTRA \
  --pluginpath=./plugins/ \
  --plugin=acthex-testplugin \
  $WHAT 
  
