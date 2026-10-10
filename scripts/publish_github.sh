#!/usr/bin/env bash
# Requires Git and GitHub CLI (gh). Run after authenticating: gh auth login.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v git >/dev/null || { echo 'Install git first.' >&2; exit 1; }
command -v gh >/dev/null || { echo 'Install GitHub CLI from https://cli.github.com/' >&2; exit 1; }
gh auth status || { echo 'First run: gh auth login' >&2; exit 1; }
if [ ! -d .git ]; then git init -b main; fi
git add .
if ! git diff --cached --quiet; then git commit -m 'feat: initial GPTmail open-source release'; fi
gh repo create ozandikici/GPTmail --public --source . --remote origin --push
echo 'Public repo: https://github.com/ozandikici/GPTmail'
