#!/bin/bash

set -o pipefail

if [[ ! $1 ]]; then
	echo "Must specify URL to check"
	exit 2
fi

curl -s -D- -o /dev/null -L -w "TELEMETRY: latency %{time_starttransfer}\nTELEMETRY: total_time %{time_total}\n" $1 | awk '{ if ($1 == "TELEMETRY:") { print $1" "$2" "$3*1000 } else {print;}}'
res=$?

echo "Check finished with status code $res"
exit $res
