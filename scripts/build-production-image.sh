#!/bin/sh
set -eu

image_tag="${1:-elden-ring-lore-graph:local}"
temporary_root="${TMPDIR:-/tmp}"
build_context="$(mktemp -d "$temporary_root/elden-lore-build.XXXXXX")"

cleanup() {
  rm -rf -- "$build_context"
}
trap cleanup EXIT INT TERM

rsync -a \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='._*' \
  --exclude='.DS_Store' \
  ./ "$build_context/"

docker build --tag "$image_tag" "$build_context"
