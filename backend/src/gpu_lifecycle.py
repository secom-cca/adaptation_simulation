from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config


class GpuLifecycleError(RuntimeError):
    pass


def _auto_wake_enabled() -> bool:
    value = (os.environ.get("GPU_AUTO_WAKE_ENABLED") or "true").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise GpuLifecycleError(
        "GPU_AUTO_WAKE_ENABLED must be true/false, yes/no, on/off, or 1/0"
    )


def _required_env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise GpuLifecycleError(f"{name} is not configured")
    return value


@lru_cache(maxsize=None)
def _client(service_name: str, region_name: str):
    return boto3.client(
        service_name,
        region_name=region_name,
        config=Config(
            retries={"total_max_attempts": 3, "mode": "adaptive"},
            connect_timeout=3,
            read_timeout=10,
        ),
    )


def _schedule_auto_stop(
    scheduler_client,
    *,
    instance_id: str,
    role_arn: str,
    stop_at: datetime,
    schedule_name: str,
    schedule_group: str,
) -> None:
    target = {
        "Arn": "arn:aws:scheduler:::aws-sdk:ec2:stopInstances",
        "RoleArn": role_arn,
        "Input": json.dumps({"InstanceIds": [instance_id]}),
    }
    schedule = {
        "Name": schedule_name,
        "GroupName": schedule_group,
        "ScheduleExpression": f"at({stop_at.strftime('%Y-%m-%dT%H:%M:%S')})",
        "FlexibleTimeWindow": {"Mode": "OFF"},
        "ActionAfterCompletion": "DELETE",
        "State": "ENABLED",
        "Target": target,
    }

    try:
        scheduler_client.get_schedule(Name=schedule_name, GroupName=schedule_group)
    except scheduler_client.exceptions.ResourceNotFoundException:
        try:
            scheduler_client.create_schedule(**schedule)
            return
        except scheduler_client.exceptions.ConflictException:
            # Another web worker created the shared schedule first.
            pass

    scheduler_client.update_schedule(**schedule)


def wake_gpu(
    *,
    ec2_client=None,
    scheduler_client=None,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not _auto_wake_enabled():
        return {
            "enabled": False,
            "state": "disabled",
            "start_requested": False,
        }

    region = (os.environ.get("AWS_REGION") or "ap-northeast-1").strip()
    instance_id = _required_env("GPU_INSTANCE_ID")
    scheduler_role_arn = _required_env("GPU_SCHEDULER_ROLE_ARN")
    schedule_name = (
        os.environ.get("GPU_AUTO_STOP_SCHEDULE_NAME")
        or "adaptation-gpu-autostop"
    ).strip()
    schedule_group = (os.environ.get("GPU_AUTO_STOP_SCHEDULE_GROUP") or "default").strip()

    try:
        auto_stop_hours = float(os.environ.get("GPU_AUTO_STOP_HOURS") or "3")
    except ValueError as exc:
        raise GpuLifecycleError("GPU_AUTO_STOP_HOURS must be a number") from exc
    if auto_stop_hours <= 0:
        raise GpuLifecycleError("GPU_AUTO_STOP_HOURS must be greater than zero")

    ec2 = ec2_client or _client("ec2", region)
    scheduler = scheduler_client or _client("scheduler", region)
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instances = [
        instance
        for reservation in response.get("Reservations", [])
        for instance in reservation.get("Instances", [])
    ]
    if not instances:
        raise GpuLifecycleError(f"GPU instance {instance_id} was not found")

    state = instances[0]["State"]["Name"]
    if state in {"shutting-down", "terminated"}:
        raise GpuLifecycleError(f"GPU instance is {state} and cannot be started")
    if state == "stopping":
        return {
            "instance_id": instance_id,
            "state": state,
            "start_requested": False,
            "retry_after_seconds": 60,
        }

    start_requested = state == "stopped"
    if start_requested:
        ec2.start_instances(InstanceIds=[instance_id])
        state = "pending"

    current_time = now or datetime.now(timezone.utc)
    stop_at = (current_time + timedelta(hours=auto_stop_hours)).replace(microsecond=0)
    _schedule_auto_stop(
        scheduler,
        instance_id=instance_id,
        role_arn=scheduler_role_arn,
        stop_at=stop_at,
        schedule_name=schedule_name,
        schedule_group=schedule_group,
    )

    return {
        "enabled": True,
        "instance_id": instance_id,
        "state": state,
        "start_requested": start_requested,
        "auto_stop_at": stop_at.isoformat(),
    }
