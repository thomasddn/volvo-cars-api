#!/usr/bin/env bash
# Setups the repository.

set -e

# Stop on errors
cd "$(dirname "$0")/.."

if [ ! -n "$VIRTUAL_ENV" ]; then
  if [ -x "$(command -v uv)" ]; then
    uv venv venv
  else
    python3 -m venv venv
  fi
  source /home/vscode/.local/vca-venv/bin/activate
fi

if ! [ -x "$(command -v uv)" ]; then
  python3 -m pip install uv
fi
