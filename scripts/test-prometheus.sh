#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

promtool check rules prometheus/rules/*.yaml prometheus/recording-rules/*.yaml
promtool test rules prometheus/tests/*.test.yaml
