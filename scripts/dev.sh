#!/usr/bin/env bash
set -euo pipefail

.venv/bin/python -m bcradio.server &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

npm run dev
