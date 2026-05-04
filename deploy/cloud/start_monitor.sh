#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${1:-$ROOT_DIR/deploy/cloud/monitor.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing monitor env file: $ENV_FILE"
  echo "Copy deploy/cloud/monitor.env.example to deploy/cloud/monitor.env and adjust the paths first."
  exit 1
fi

cd "$ROOT_DIR/monitor"
docker compose --env-file "$ENV_FILE" up -d --build

echo "Monitor started. Open: http://<server-ip>:$(grep '^FLASK_PORT=' "$ENV_FILE" | cut -d '=' -f2)"
