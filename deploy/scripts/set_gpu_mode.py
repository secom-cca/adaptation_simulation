#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


REGISTERABLE_TASK_FIELDS = {
    "containerDefinitions",
    "cpu",
    "enableFaultInjection",
    "ephemeralStorage",
    "executionRoleArn",
    "family",
    "inferenceAccelerators",
    "ipcMode",
    "memory",
    "networkMode",
    "pidMode",
    "placementConstraints",
    "proxyConfiguration",
    "requiresCompatibilities",
    "runtimePlatform",
    "taskRoleArn",
    "volumes",
}


def _client_config() -> Config:
    return Config(
        retries={"total_max_attempts": 4, "mode": "adaptive"},
        connect_timeout=5,
        read_timeout=30,
    )


def _replace_environment(
    task_definition: dict[str, Any],
    replacements: dict[str, str],
) -> dict[str, Any]:
    updated = copy.deepcopy(task_definition)
    containers = updated.get("containerDefinitions", [])
    container = next((item for item in containers if item.get("name") == "web"), None)
    if container is None:
        raise RuntimeError("The ECS task definition has no container named 'web'")

    environment = container.get("environment", [])
    environment = [item for item in environment if item.get("name") not in replacements]
    environment.extend(
        {"name": name, "value": value}
        for name, value in replacements.items()
    )
    container["environment"] = environment
    return updated


def _registration_payload(task_definition: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in task_definition.items()
        if key in REGISTERABLE_TASK_FIELDS
    }


def _current_task_definition(ecs, cluster: str, service_name: str) -> dict[str, Any]:
    response = ecs.describe_services(cluster=cluster, services=[service_name])
    if not response.get("services"):
        raise RuntimeError(f"ECS service {cluster}/{service_name} was not found")
    task_definition_arn = response["services"][0]["taskDefinition"]
    return ecs.describe_task_definition(taskDefinition=task_definition_arn)["taskDefinition"]


def _gpu_private_ip(ec2, instance_id: str) -> str:
    response = ec2.describe_instances(InstanceIds=[instance_id])
    instances = [
        instance
        for reservation in response.get("Reservations", [])
        for instance in reservation.get("Instances", [])
    ]
    if not instances or not instances[0].get("PrivateIpAddress"):
        raise RuntimeError(f"GPU instance {instance_id} has no private IP address")
    return instances[0]["PrivateIpAddress"]


def _delete_auto_stop_schedule(scheduler, name: str, group: str) -> None:
    try:
        scheduler.get_schedule(Name=name, GroupName=group)
    except scheduler.exceptions.ResourceNotFoundException:
        return
    scheduler.delete_schedule(Name=name, GroupName=group)


def _stop_gpu(ec2, instance_id: str) -> str:
    response = ec2.describe_instances(InstanceIds=[instance_id])
    state = response["Reservations"][0]["Instances"][0]["State"]["Name"]
    if state in {"pending", "running"}:
        ec2.stop_instances(InstanceIds=[instance_id])
        ec2.get_waiter("instance_stopped").wait(
            InstanceIds=[instance_id],
            WaiterConfig={"Delay": 15, "MaxAttempts": 40},
        )
        return "stopped"
    if state == "stopping":
        ec2.get_waiter("instance_stopped").wait(
            InstanceIds=[instance_id],
            WaiterConfig={"Delay": 15, "MaxAttempts": 40},
        )
        return "stopped"
    return state


def _mode_status(ecs, ec2, scheduler, args) -> dict[str, Any]:
    task = _current_task_definition(ecs, args.cluster, args.service)
    container = next(
        item for item in task["containerDefinitions"] if item.get("name") == "web"
    )
    environment = {item["name"]: item["value"] for item in container.get("environment", [])}
    instance = ec2.describe_instances(InstanceIds=[args.instance_id])
    instance_state = instance["Reservations"][0]["Instances"][0]["State"]["Name"]
    try:
        schedule = scheduler.get_schedule(Name=args.schedule_name, GroupName=args.schedule_group)
        schedule_expression = schedule["ScheduleExpression"]
    except scheduler.exceptions.ResourceNotFoundException:
        schedule_expression = None

    return {
        "mode": "on" if environment.get("GPU_AUTO_WAKE_ENABLED", "true").lower() == "true" else "off",
        "ollama_host": environment.get("OLLAMA_HOST"),
        "gpu_instance_state": instance_state,
        "auto_stop_schedule": schedule_expression,
        "task_definition": task["taskDefinitionArn"],
    }


def set_mode(args) -> dict[str, Any]:
    config = _client_config()
    ecs = boto3.client("ecs", region_name=args.region, config=config)
    ec2 = boto3.client("ec2", region_name=args.region, config=config)
    scheduler = boto3.client("scheduler", region_name=args.region, config=config)

    if args.mode == "status":
        return _mode_status(ecs, ec2, scheduler, args)

    private_ip = _gpu_private_ip(ec2, args.instance_id)
    enabled = args.mode == "on"
    replacements = {
        "GPU_AUTO_WAKE_ENABLED": "true" if enabled else "false",
        "GPU_INSTANCE_ID": args.instance_id,
        "GPU_SCHEDULER_ROLE_ARN": args.scheduler_role_arn,
        "GPU_AUTO_STOP_HOURS": str(args.auto_stop_hours),
        "OLLAMA_HOST": f"http://{private_ip}:11434" if enabled else "http://127.0.0.1:11434",
    }

    current = _current_task_definition(ecs, args.cluster, args.service)
    updated = _replace_environment(current, replacements)
    registered = ecs.register_task_definition(**_registration_payload(updated))
    task_definition_arn = registered["taskDefinition"]["taskDefinitionArn"]
    ecs.update_service(
        cluster=args.cluster,
        service=args.service,
        taskDefinition=task_definition_arn,
    )
    ecs.get_waiter("services_stable").wait(
        cluster=args.cluster,
        services=[args.service],
        WaiterConfig={"Delay": 15, "MaxAttempts": 40},
    )

    gpu_state = None
    if not enabled:
        _delete_auto_stop_schedule(scheduler, args.schedule_name, args.schedule_group)
        gpu_state = _stop_gpu(ec2, args.instance_id)

    return {
        "mode": args.mode,
        "task_definition": task_definition_arn,
        "gpu_instance_state": gpu_state or "starts on next game",
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Switch the deployed game's GPU mode")
    parser.add_argument("mode", choices=("on", "off", "status"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "ap-northeast-1"))
    parser.add_argument("--cluster", default=os.environ.get("ECS_CLUSTER", "adaptation"))
    parser.add_argument("--service", default=os.environ.get("ECS_SERVICE", "adaptation-web"))
    parser.add_argument("--instance-id", default=os.environ.get("GPU_INSTANCE_ID"), required=False)
    parser.add_argument(
        "--scheduler-role-arn",
        default=os.environ.get("SCHEDULER_ROLE_ARN"),
        required=False,
    )
    parser.add_argument("--auto-stop-hours", type=float, default=3)
    parser.add_argument("--schedule-name", default="adaptation-gpu-autostop")
    parser.add_argument("--schedule-group", default="default")
    args = parser.parse_args()
    if not args.instance_id:
        parser.error("--instance-id or GPU_INSTANCE_ID is required")
    if args.mode != "status" and not args.scheduler_role_arn:
        parser.error("--scheduler-role-arn or SCHEDULER_ROLE_ARN is required")
    return args


def main() -> int:
    args = _parse_args()
    try:
        result = set_mode(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ClientError, RuntimeError) as exc:
        print(f"GPU mode switch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
