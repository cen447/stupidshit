#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${1:-git+https://github.com/cen447/parallel_smoke.git}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required."
  exit 1
fi

python3 -m pip install --user --upgrade pip pipx
python3 -m pipx ensurepath || true
python3 -m pipx install --force "$REPO_URL"

cat <<'EOF'

Install complete.
If command is not found yet, open a new terminal.

Run from anywhere:
  fuck asad 1
  fuck asad 10
EOF

