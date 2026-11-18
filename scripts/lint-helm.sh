#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
chart_cache="$(mktemp -d)"
trap 'rm -rf -- "$chart_cache"' EXIT

chart_version() {
  local variable="$1" file="$2" value
  value="$(awk -v variable="$variable" '
    $1 == "variable" && $2 == "\"" variable "\"" { found = 1; next }
    found && $1 == "}" { exit }
    found && $1 == "default" && $2 == "=" { print $3; exit }
  ' "$file")"
  if [[ ! "$value" =~ ^\"([0-9]+\.[0-9]+\.[0-9]+([-+][a-zA-Z0-9.-]+)?)\"$ ]]; then
    printf 'Expected a pinned chart version for %s in %s\n' "$variable" "$file" >&2
    return 1
  fi
  printf '%s\n' "${BASH_REMATCH[1]}"
}

lint_chart() {
  local chart="$1" repo="$2" version="$3"
  shift 3
  local destination="$chart_cache/$chart-$version"
  local chart_dir="$destination/$chart"
  if [[ ! -d "$chart_dir" ]]; then
    mkdir -p "$destination"
    helm pull "$chart" --repo "$repo" --version "$version" --untar --destination "$destination"

    if [[ "$chart" == opentelemetry-operator && "$version" == 0.83.0 ]]; then
      # The upstream chart ships a string in an annotation that must be an array.
      # Normalize only the downloaded copy so Helm can validate the whole schema.
      python3 - "$chart_dir/values.schema.json" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
schema = json.loads(path.read_text(encoding="utf-8"))
feature_gates = schema["properties"]["manager"]["properties"]["featureGates"]
if isinstance(feature_gates.get("examples"), str):
    feature_gates["examples"] = [feature_gates["examples"]]
    path.write_text(json.dumps(schema), encoding="utf-8")
PY
    fi
  fi

  printf '[helm lint] %s %s (%s)\n' "$chart" "$version" "$environment"
  helm lint "$chart_dir" "$@"
}

prometheus_repo="https://prometheus-community.github.io/helm-charts"
otel_repo="https://open-telemetry.github.io/opentelemetry-helm-charts"
prometheus_values="$ROOT_DIR/helm/kube-prometheus-stack/values"
collector_values="$ROOT_DIR/helm/otel-collector/values"

for environment in dev stage prod; do
  variables="$ROOT_DIR/terraform/environments/$environment/variables.tf"
  prometheus_version="$(chart_version kube_prometheus_stack_chart_version "$variables")"
  collector_version="$(chart_version otel_collector_chart_version "$variables")"
  operator_version="$(chart_version otel_operator_chart_version "$variables")"

  lint_chart kube-prometheus-stack "$prometheus_repo" "$prometheus_version" \
    -f "$prometheus_values/base.yaml" -f "$prometheus_values/$environment.yaml"
  lint_chart opentelemetry-collector "$otel_repo" "$collector_version" \
    -f "$collector_values/base.yaml" -f "$collector_values/$environment.yaml"
  lint_chart opentelemetry-operator "$otel_repo" "$operator_version" \
    -f "$ROOT_DIR/helm/otel-operator/values.yaml"
done
