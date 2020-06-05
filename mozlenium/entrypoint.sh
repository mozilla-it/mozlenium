#!/bin/bash

head -1 $1 || true

start=$(date +%s)
node $*
end=$(date +%s)

((runtime=end-start))

echo "Check finished in ${runtime:-0} seconds"
