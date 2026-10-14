#!/usr/bin/env bash
# Deploy salvage engine to CloudBase CloudRun (build context = ming-salvage-sim-main/).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SALVAGE="$ROOT/ming-salvage-sim-main"

if ! command -v tcb >/dev/null 2>&1; then
  echo "tcb CLI not found. Install: npm install -g @cloudbase/cli" >&2
  exit 1
fi

cp "$ROOT/cloudrun/salvage/Dockerfile" "$SALVAGE/Dockerfile"
cp "$SALVAGE/requirements.txt" "$SALVAGE/requirements.txt.bak"
cp "$ROOT/cloudrun/salvage/requirements.txt" "$SALVAGE/requirements.txt"
if [ -f "$SALVAGE/.dockerignore" ]; then
  cp "$SALVAGE/.dockerignore" "$SALVAGE/.dockerignore.bak"
fi
cp "$ROOT/cloudrun/salvage/.dockerignore" "$SALVAGE/.dockerignore"
trap 'rm -f "$SALVAGE/Dockerfile"; mv -f "$SALVAGE/requirements.txt.bak" "$SALVAGE/requirements.txt" 2>/dev/null || rm -f "$SALVAGE/requirements.txt.bak"; if [ -f "$SALVAGE/.dockerignore.bak" ]; then mv -f "$SALVAGE/.dockerignore.bak" "$SALVAGE/.dockerignore"; else rm -f "$SALVAGE/.dockerignore"; fi' EXIT

cd "$SALVAGE"
TCB=(tcb)
if [ -n "${TCB_ENV_ID:-}" ]; then
  TCB=(tcb -e "$TCB_ENV_ID")
fi

echo "Deploying ai-assistant-salvage from $SALVAGE (port 8080)..."
"${TCB[@]}" cloudrun deploy -s ai-assistant-salvage --source . --port 8080 "$@"
