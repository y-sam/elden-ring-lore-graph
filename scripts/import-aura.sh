#!/usr/bin/env bash
set -euo pipefail

read -rp "AuraDB connection URI: " NEO4J_URI
read -rp "AuraDB username [neo4j]: " NEO4J_USERNAME
NEO4J_USERNAME=${NEO4J_USERNAME:-neo4j}
read -rsp "AuraDB password: " NEO4J_PASSWORD
printf '\n'
read -rp "AuraDB database [neo4j]: " NEO4J_DATABASE
NEO4J_DATABASE=${NEO4J_DATABASE:-neo4j}

printf 'This will synchronize the validated curated dataset with %s.\n' "$NEO4J_URI"
read -rp 'Type IMPORT to continue: ' confirmation
if [[ "$confirmation" != "IMPORT" ]]; then
  printf 'Import cancelled.\n'
  exit 1
fi

export APP_ENV=development
export NEO4J_URI NEO4J_USERNAME NEO4J_PASSWORD NEO4J_DATABASE
export UV_PROJECT_ENVIRONMENT=${UV_PROJECT_ENVIRONMENT:-/tmp/elden-lore-venv}
export UV_CACHE_DIR=${UV_CACHE_DIR:-/tmp/elden-lore-uv-cache}

uv run elden-lore-audit
uv run elden-lore-import

unset NEO4J_PASSWORD
printf 'AuraDB synchronization completed.\n'
