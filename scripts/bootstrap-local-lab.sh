#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_DIR="$ROOT_DIR/docker-compose/local-lab"
CERT_DIR="$ROOT_DIR/.local-lab/certs"
PROM_WEB="$LAB_DIR/prometheus/web.yml"
ALERT_WEB="$LAB_DIR/alertmanager/web.yml"

umask 077
mkdir -p "$ROOT_DIR/.local-lab"
chmod 0700 "$ROOT_DIR/.local-lab"
mkdir -p "$CERT_DIR"
chmod 0755 "$CERT_DIR"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "Created .env from .env.example"
fi

if [[ ! -f "$CERT_DIR/tls.crt" || ! -f "$CERT_DIR/tls.key" ]]; then
  openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
    -keyout "$CERT_DIR/tls.key" \
    -out "$CERT_DIR/tls.crt" \
    -subj "/CN=localhost"
  chmod 0644 "$CERT_DIR/tls.crt" "$CERT_DIR/tls.key"
  echo "Certificados locais gerados dentro do diretório privado .local-lab"
fi

python3 "$ROOT_DIR/scripts/prepare-local-auth.py"
echo "Bootstrap local concluído; use scripts/up-local-lab.sh. Não há senha padrão."
