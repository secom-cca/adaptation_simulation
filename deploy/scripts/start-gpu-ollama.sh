#!/usr/bin/env bash
# Start GPU EC2 (Ollama), wait until running, schedule auto-stop.
# Usage:
#   ./deploy/scripts/start-gpu-ollama.sh
#   AUTO_STOP_AFTER_HOURS=6 ./deploy/scripts/start-gpu-ollama.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib.sh"

load_env
require_cmd aws
require_cmd python3
require_var GPU_INSTANCE_ID
require_var AWS_REGION
require_var SCHEDULER_ROLE_ARN

HOURS="${AUTO_STOP_AFTER_HOURS:-3}"
NAME="$(schedule_name)"
GROUP="${AUTO_STOP_SCHEDULE_GROUP:-default}"

echo "==> Starting instance ${GPU_INSTANCE_ID} (${AWS_REGION})..."
aws ec2 start-instances \
  --region "${AWS_REGION}" \
  --instance-ids "${GPU_INSTANCE_ID}" \
  >/dev/null

echo "==> Waiting for instance running..."
aws ec2 wait instance-running \
  --region "${AWS_REGION}" \
  --instance-ids "${GPU_INSTANCE_ID}"

PRIVATE_IP="$(aws ec2 describe-instances \
  --region "${AWS_REGION}" \
  --instance-ids "${GPU_INSTANCE_ID}" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)"

echo "==> Instance running at private IP ${PRIVATE_IP}"
echo "    ECS OLLAMA_HOST should be http://${PRIVATE_IP}:11434 (update task def if IP changed)."
echo "==> Allow ~1–3 minutes for Ollama systemd/docker to finish starting."

STOP_AT_UTC="$(python3 - <<PY
from datetime import datetime, timedelta, timezone
hours = float("${HOURS}")
when = datetime.now(timezone.utc) + timedelta(hours=hours)
print(when.strftime("%Y-%m-%dT%H:%M:%S"))
PY
)"

STOP_AT_LOCAL="$(python3 - <<PY
from datetime import datetime, timedelta
hours = float("${HOURS}")
when = datetime.now().astimezone() + timedelta(hours=hours)
print(when.strftime("%Y-%m-%d %H:%M:%S %Z"))
PY
)"

TARGET_FILE="$(mktemp)"
trap 'rm -f "${TARGET_FILE}"' EXIT
python3 - <<PY >"${TARGET_FILE}"
import json
print(json.dumps({
    "Arn": "arn:aws:scheduler:::aws-sdk:ec2:stopInstances",
    "RoleArn": "${SCHEDULER_ROLE_ARN}",
    "Input": json.dumps({"InstanceIds": ["${GPU_INSTANCE_ID}"]}),
}))
PY

echo "==> Scheduling auto-stop at ${STOP_AT_UTC} UTC (${STOP_AT_LOCAL}, +${HOURS}h)..."

if aws scheduler get-schedule \
    --region "${AWS_REGION}" \
    --name "${NAME}" \
    --group-name "${GROUP}" >/dev/null 2>&1; then
  aws scheduler delete-schedule \
    --region "${AWS_REGION}" \
    --name "${NAME}" \
    --group-name "${GROUP}" >/dev/null
fi

aws scheduler create-schedule \
  --region "${AWS_REGION}" \
  --name "${NAME}" \
  --group-name "${GROUP}" \
  --schedule-expression "at(${STOP_AT_UTC})" \
  --flexible-time-window Mode=OFF \
  --action-after-completion DELETE \
  --target "file://${TARGET_FILE}" >/dev/null

echo ""
echo "GPU / Ollama start requested."
echo "  Instance:     ${GPU_INSTANCE_ID}"
echo "  Private IP:   ${PRIVATE_IP}"
echo "  Auto-stop:    ${STOP_AT_LOCAL} (schedule: ${NAME})"
echo "  Manual stop:  ./deploy/scripts/stop-gpu-ollama.sh"
echo ""
