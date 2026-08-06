#!/usr/bin/env bash
set -euo pipefail

target="${1:-$PWD}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
starter="$(cd "$script_dir/../templates/vinext-starter" && pwd)"

mkdir -p "$target"
if find "$target" -mindepth 1 -maxdepth 1 \
  ! -name '.git' ! -name '.DS_Store' ! -name 'work' ! -name 'outputs' \
  -print -quit | grep -q .; then
  echo "Target is not empty: $target" >&2
  exit 2
fi

cp -R "$starter"/. "$target"/
cd "$target"
if [[ ! -d .git ]]; then
  git init -b main >/dev/null
fi
npm ci --ignore-scripts --prefer-offline --no-audit --no-fund
