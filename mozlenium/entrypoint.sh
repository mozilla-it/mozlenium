#!/bin/bash

head -1 $1 || true

start=$(date +%s)
node $*
res=$?
end=$(date +%s)

((runtime=end-start))

echo "Check finished in ${runtime:-0} seconds with status code $res"

exit $res
