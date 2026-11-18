#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_DIR="$ROOT_DIR/docker-compose/local-lab"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "Missing .env file. Copy .env.example to .env first."
  exit 1
fi

test -f "$ROOT_DIR/.local-lab/lab.env" || { echo "Execute scripts/bootstrap-local-lab.sh primeiro."; exit 1; }
cd "$LAB_DIR"
docker compose --env-file "$ROOT_DIR/.local-lab/lab.env" pull
docker compose --env-file "$ROOT_DIR/.local-lab/lab.env" up -d

echo "Local lab is running:"
echo "- Grafana: https://localhost:3000"
echo "- Prometheus: https://localhost:9090"
echo "- Alertmanager: https://localhost:9093"
