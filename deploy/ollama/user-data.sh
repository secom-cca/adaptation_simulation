#!/bin/bash
# EC2 user-data for the GPU Ollama host.
# Target AMI: "Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 24.04)"
#   (NVIDIA driver, Docker and NVIDIA Container Toolkit are preinstalled).
# The placeholder in the heredoc below is replaced with deploy/ollama/docker-compose.yml when the
# launch template is created (see README A8). Runs on first boot only; after
# that Docker restarts the ollama container (restart: unless-stopped).
set -euxo pipefail

systemctl enable --now docker

if ! docker compose version >/dev/null 2>&1; then
  apt-get update
  apt-get install -y docker-compose-plugin || apt-get install -y docker-compose-v2
fi

mkdir -p /opt/adaptation-ollama
cat > /opt/adaptation-ollama/docker-compose.yml <<'COMPOSE_EOF'
__COMPOSE_YML__
COMPOSE_EOF

cd /opt/adaptation-ollama
docker compose up -d ollama
docker compose run --rm ollama-pull
