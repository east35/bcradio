#!/usr/bin/env bash
set -euo pipefail

if ! command -v mpv >/dev/null 2>&1; then
  echo "mpv is required but was not found on PATH." >&2
  echo "macOS: brew install mpv" >&2
  echo "Raspberry Pi OS: sudo apt update && sudo apt install -y mpv" >&2
  exit 127
fi

mpv --idle=yes --no-video --input-ipc-server=/tmp/bc-radio-mpv.sock
