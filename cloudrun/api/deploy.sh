#!/usr/bin/env bash
# Deploy main API to CloudBase CloudRun (build context = repo root).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if ! command -v tcb >/dev/null 2>&1; then
  echo "tcb CLI not found. Install: npm install -g @cloudbase/cli" >&2
  exit 1
fi

cp cloudrun/api/Dockerfile ./Dockerfile
trap 'rm -f ./Dockerfile' EXIT

TCB=(tcb)
if [ -n "${TCB_ENV_ID:-}" ]; then
  TCB=(tcb -e "$TCB_ENV_ID")
fi

echo "Deploying ai-assistant-api from $ROOT (port 8080)..."
"${TCB[@]}" cloudrun deploy -s ai-assistant-api --source . --port 8080 "$@"
