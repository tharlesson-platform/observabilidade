#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

check_bin() {
  local bin="$1"
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Missing dependency: $bin" >&2
    return 1
  fi
}

check_bin terraform
check_bin docker
check_bin helm

for env in dev stage prod; do
  echo "[terraform fmt/validate] $env"
  terraform -chdir="$ROOT_DIR/terraform/environments/$env" fmt -check -recursive
  if [[ -d "$ROOT_DIR/terraform/environments/$env/.terraform" ]]; then
    terraform -chdir="$ROOT_DIR/terraform/environments/$env" validate
  else
    echo "Skipping terraform validate for $env (run terraform init first)."
  fi
done

bash "$ROOT_DIR/scripts/lint-helm.sh"

echo "[docker compose config]"
docker compose -f "$ROOT_DIR/docker-compose/local-lab/docker-compose.yml" config >/dev/null

echo "Validation completed."
