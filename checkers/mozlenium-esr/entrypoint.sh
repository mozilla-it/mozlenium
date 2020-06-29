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

export PATH=${PATH}:${NODE_PATH}/geckodriver/bin

#geckodriver -V
#firefox --version

start=$(date +%s)
node --abort-on-uncaught-exception --unhandled-rejections=strict $f $*
res=$?
end=$(date +%s)

((runtime=end-start))

echo "Check finished in ${runtime:-0} seconds with status code $res"

exit $res
