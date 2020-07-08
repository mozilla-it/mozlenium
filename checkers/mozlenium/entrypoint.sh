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

if [[ -e /app/extra.sh ]]; then
  # in case anyone is using this as a 
  # base image and wants to inject some
  # special sauce
  source /app/extra.sh
fi

if [[ ${WRAPPER:-1} -eq 1 ]]; then
  # the wrapper edition!
  echo 'async function runner($browser, $driver, $secure) {' > check.js
  cat $f | grep -v "require('mozlenium')();" | sed 's|^$browser\.|return $browser.|' >> check.js
  echo -e '}\n\nmodule.exports = runner;' >> check.js
  f=wrapper.js
fi


#geckodriver -V
#firefox --version

stime=$(date +%s%3N)
node --abort-on-uncaught-exception --unhandled-rejections=strict $f $browser
res=$?
etime=$(date +%s%3N)

((runtime=etime-stime))

echo "Check finished in ${runtime:-0} ms with status code $res"
echo TELEMETRY: node_time ${runtime:-0}

exit $res
