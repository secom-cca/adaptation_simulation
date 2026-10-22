#!/usr/bin/env bash
# Switch the deployed application between GPU auto-wake and fallback-only mode.
# Usage: ./deploy/scripts/set-gpu-mode.sh on|off|status

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/deploy/.env.aws"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

MODE="${1:-status}"
PYTHON="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  PYTHON="$(command -v python3 || true)"
fi
if [[ -z "${PYTHON}" ]] || ! "${PYTHON}" -c 'import boto3' >/dev/null 2>&1; then
  echo "Python with boto3 is required. Run: python3 -m pip install boto3" >&2
  exit 1
fi

exec "${PYTHON}" "${SCRIPT_DIR}/set_gpu_mode.py" "${MODE}" \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --instance-id "${GPU_INSTANCE_ID}" \
  --scheduler-role-arn "${SCHEDULER_ROLE_ARN}" \
  --auto-stop-hours "${AUTO_STOP_AFTER_HOURS:-3}"
