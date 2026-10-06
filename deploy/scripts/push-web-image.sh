#!/usr/bin/env bash
# Build the web Docker image, push to ECR, force ECS redeploy.
# Usage (from repo root or any cwd):
#   ./deploy/scripts/push-web-image.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

load_env
require_cmd aws
require_cmd docker
require_var AWS_REGION
require_var AWS_ACCOUNT_ID
require_var ECR_REPOSITORY
require_var ECS_CLUSTER
require_var ECS_SERVICE

TAG="${IMAGE_TAG:-latest}"
URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:${TAG}"

echo "==> ECR login..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin \
    "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Building image..."
docker build -t "${ECR_REPOSITORY}:${TAG}" "${ROOT_DIR}"

echo "==> Tagging ${URI}..."
docker tag "${ECR_REPOSITORY}:${TAG}" "${URI}"

echo "==> Pushing..."
docker push "${URI}"

echo "==> Forcing ECS new deployment..."
aws ecs update-service \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --force-new-deployment >/dev/null

echo ""
echo "Pushed ${URI} and requested ECS redeploy (${ECS_CLUSTER}/${ECS_SERVICE})."
echo ""
