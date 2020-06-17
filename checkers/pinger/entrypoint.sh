#!/bin/bash

if [[ ! $1 ]]; then
	echo "Must specify URL to check"
	exit 2
fi

wget -S -O- $1 >/dev/null
res=$?

echo "Check finished with status code $res"
exit $res
