#!/usr/bin/env bash
# Shared helpers for deploy scripts.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEPLOY_DIR="${ROOT_DIR}/deploy"
ENV_FILE="${DEPLOY_DIR}/.env.aws"

load_env() {
  if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck disable=SC1090
    set -a
    source "${ENV_FILE}"
    set +a
  else
    echo "Missing ${ENV_FILE}" >&2
    echo "Copy deploy/.env.aws.example to deploy/.env.aws and fill values." >&2
    exit 1
  fi
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Environment variable ${name} is required (set in deploy/.env.aws)." >&2
    exit 1
  fi
}

schedule_name() {
  echo "${AUTO_STOP_SCHEDULE_NAME:-adaptation-gpu-autostop}"
}
