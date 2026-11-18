#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$ROOT_DIR/artifacts"
evidence="$(mktemp -d "$ROOT_DIR/artifacts/alert-smoke.XXXXXXXX")"
suffix="$(basename "$evidence" | tr '[:upper:]' '[:lower:]' | tr '.' '-')"
compose=(docker compose --project-name "observabilidade-$suffix" -f "$ROOT_DIR/docker-compose/local-lab/alert-smoke/compose.yaml")

trap '"${compose[@]}" down --volumes >>"$evidence/compose.log" 2>&1' EXIT
printf 'Alert lifecycle evidence: %s\n' "$evidence"
status=0
"${compose[@]}" up --abort-on-container-exit --exit-code-from fixture >"$evidence/compose.log" 2>&1 || status=$?
if ! "${compose[@]}" cp fixture:/tmp/evidence/. "$evidence/"; then
  tail -n 40 "$evidence/compose.log" >&2
  exit 1
fi
if [[ "$status" -ne 0 ]]; then
  tail -n 40 "$evidence/compose.log" >&2
  exit "$status"
fi
test -s "$evidence/firing.json"
test -s "$evidence/resolved.json"
printf 'Confirmed firing and resolved notifications.\n'
