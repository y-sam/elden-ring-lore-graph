#!/usr/bin/env bash
set -euo pipefail

base_url=${1:-https://elden-ring-lore-graph.onrender.com}
base_url=${base_url%/}

curl --fail --silent --show-error --retry 2 --max-time 90 "${base_url}/health" | grep -q '"status":"ok"'
curl --fail --silent --show-error --retry 2 --max-time 90 "${base_url}/ready" | grep -q '"status":"ready"'
curl --fail --silent --show-error --retry 2 --max-time 90 \
  "${base_url}/api/v1/answers?q=Who%20is%20Blaidd%3F&lang=en" | grep -q '"status":"supported"'

printf 'Production smoke check passed for %s\n' "$base_url"
