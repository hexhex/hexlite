#PYTHONPATH="/home/ps/bin/clingo-5_bb7ab74/pyclingo/:$PYTHONPATH"
WHAT="./tests/extatom2_extra.hex"
WHAT="./tests/anonymousvariable1.hex"
WHAT="./tests/choicerule6.hex"
EXTRA=""
EXTRA="$EXTRA --debug"
hexlite $EXTRA \
  --pluginpath=./plugins/ \
  --plugin=stringplugin --plugin=testplugin \
  $WHAT 
  
