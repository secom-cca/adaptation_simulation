#!/usr/bin/env bash
# Cancel auto-stop schedule (if any) and stop GPU EC2.
# Usage:
#   ./deploy/scripts/stop-gpu-ollama.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

load_env
require_cmd aws
require_var GPU_INSTANCE_ID
require_var AWS_REGION

NAME="$(schedule_name)"
GROUP="${AUTO_STOP_SCHEDULE_GROUP:-default}"

echo "==> Cancelling auto-stop schedule (${NAME}) if present..."
if aws scheduler get-schedule \
    --region "${AWS_REGION}" \
    --name "${NAME}" \
    --group-name "${GROUP}" >/dev/null 2>&1; then
  aws scheduler delete-schedule \
    --region "${AWS_REGION}" \
    --name "${NAME}" \
    --group-name "${GROUP}" >/dev/null
  echo "    Schedule deleted."
else
  echo "    No schedule found."
fi

echo "==> Stopping instance ${GPU_INSTANCE_ID}..."
aws ec2 stop-instances \
  --region "${AWS_REGION}" \
  --instance-ids "${GPU_INSTANCE_ID}" \
  >/dev/null

echo "==> Waiting for stopped..."
aws ec2 wait instance-stopped \
  --region "${AWS_REGION}" \
  --instance-ids "${GPU_INSTANCE_ID}"

STATE="$(aws ec2 describe-instances \
  --region "${AWS_REGION}" \
  --instance-ids "${GPU_INSTANCE_ID}" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)"

echo ""
echo "GPU instance state: ${STATE}"
echo ""
