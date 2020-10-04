#!/bin/bash

f=$(ls /checks/*.js | head -1)

browser=${1:-firefox}
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

export CHECKS_BASEDIR=/checks/

#geckodriver -V
#firefox --version

stime=$(date +%s%3N)
node --abort-on-uncaught-exception --unhandled-rejections=strict ./mozlenium.js -browser $browser
res=$?
etime=$(date +%s%3N)

((runtime=etime-stime))

echo "[STATUSMSG]: Check finished in ${runtime:-0} ms with status code $res"
echo "[TELEMETRY|node_time]: ${runtime:-0}"

exit $res
