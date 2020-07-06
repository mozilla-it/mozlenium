#!/bin/bash

if [[ "$1" ]]; then
  f=$1
  shift
else
  f=$(ls /checks/*.js | head -1)
fi

if [[ ! "$f" ]]; then
  echo "No check file specified"
  exit 2
fi

if [[ ! -e $f ]]; then
  echo "Could not find $f"
  exit 2
fi

export NODE_PATH=/app/node_modules

export PATH=${PATH}:${NODE_PATH}/geckodriver/bin:/app/firefox

if [[ -e /app/extra.sh ]]; then
  # in case anyone is using this as a 
  # base image and wants to inject some
  # special sauce
  source /app/extra.sh
fi

#geckodriver -V
#firefox --version

stime=$(date +%s%3N)
node --abort-on-uncaught-exception --unhandled-rejections=strict $f $*
res=$?
etime=$(date +%s%3N)

((runtime=etime-stime))

echo "Check finished in ${runtime:-0} ms with status code $res"
echo TELEMETRY: node_time ${runtime:-0}

exit $res
