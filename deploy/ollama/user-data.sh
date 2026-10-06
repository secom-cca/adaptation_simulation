#!/bin/bash
# Optional EC2 user-data snippet: install Docker + NVIDIA toolkit + start Ollama compose.
# Review before use; adjust for your AMI.
set -euxo pipefail

apt-get update
apt-get install -y docker.io docker-compose-v2 curl
systemctl enable --now docker

# Place compose files (operator should scp deploy/ollama into /opt/adaptation-ollama)
mkdir -p /opt/adaptation-ollama
if [[ -f /opt/adaptation-ollama/docker-compose.yml ]]; then
  cd /opt/adaptation-ollama
  docker compose up -d
  docker compose run --rm ollama-pull || true
fi
