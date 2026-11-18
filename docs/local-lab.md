# Laboratorio local

## Pre-requisitos

- Docker + plugin Docker Compose
- OpenSSL
- Opcional: `htpasswd` (caso contrario, o bootstrap usa container httpd)

## Inicio rapido

```bash
cp .env.example .env
make bootstrap-local
make up-local
```

Endpoints:

- Grafana: https://localhost:3000
- Prometheus: https://localhost:9090
- Alertmanager: https://localhost:9093

Credenciais padrao do laboratorio:

- Grafana: `admin / change-me` (sobrescreva via `.env`)
- Basic auth do Prometheus: `prom_admin / prom-admin-change-me`
- Basic auth do Alertmanager: `alert_admin / alert-admin-change-me`

## Apps de exemplo (opcional)

```bash
docker compose -f docker-compose/local-lab/docker-compose.yml --profile examples up -d --build
```

- App Node: http://localhost:8081
- App Python: http://localhost:8082
- App Java: http://localhost:8083

## Testar disparo e resolução de um alerta

```bash
make smoke-alerts
```

Esse comando inicia um projeto Docker Compose isolado, com a regra
`BlackboxEndpointDown` do repositório. Um endpoint sintético troca
HTTP 200 por 503. O Blackbox Exporter mede a falha, o Collector
exporta `probe_success` e o Prometheus avalia a regra com os três minutos
de espera originais. Depois da notificação de disparo, o endpoint volta a
responder 200 e o Alertmanager envia a resolução ao webhook do laboratório.

Reserve cerca de quatro a cinco minutos após o download das imagens.
A rede do cenário é interna e o webhook é local ao projeto Compose. O comando
remove os containers, a rede e os volumes desse cenário ao terminar.
Os arquivos `firing.json` e `resolved.json` ficam em `artifacts/alert-smoke.*`,
com timestamps, estado do probe, evidência do Prometheus e payload recebido do Alertmanager.

## Parar

```bash
make down-local
```

## Observacoes

- Os certificados TLS sao self-signed e servem apenas para laboratorio.
- Troque as senhas geradas de basic auth em qualquer ambiente compartilhado.
- O laboratorio local usa stack OSS central (sem AMP).
