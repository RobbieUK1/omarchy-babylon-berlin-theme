#!/usr/bin/env bash
# Unified installer: local checkout or curl .../install.sh | bash
set -euo pipefail
repo='https://github.com/RobbieUK1/omarchy-babylon-berlin-theme.git'
source_path=${BASH_SOURCE[0]:-}
if [[ -n "$source_path" && -f "$source_path" && -d "$(dirname -- "$source_path")/backgrounds" ]]; then
  root=$(cd -- "$(dirname -- "$source_path")" && pwd)
else
  command -v git >/dev/null || { echo 'git is required' >&2; exit 1; }
  temporary=$(mktemp -d)
  trap 'rm -rf -- "$temporary"' EXIT
  git clone --depth 1 --branch main "$repo" "$temporary/theme"
  root="$temporary/theme"
fi
python3 "$root/scripts/install-theme.py" "$@"
