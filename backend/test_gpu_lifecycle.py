import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.append(str(Path(__file__).parent / "src"))

from gpu_lifecycle import GpuLifecycleError, wake_gpu


class ResourceNotFoundException(Exception):
    pass


class ConflictException(Exception):
    pass


def scheduler_mock(*, exists: bool):
    scheduler = Mock()
    scheduler.exceptions.ResourceNotFoundException = ResourceNotFoundException
    scheduler.exceptions.ConflictException = ConflictException
    if not exists:
        scheduler.get_schedule.side_effect = ResourceNotFoundException()
    return scheduler


class WakeGpuTest(unittest.TestCase):
    env = {
        "AWS_REGION": "ap-northeast-1",
        "GPU_INSTANCE_ID": "i-0123456789abcdef0",
        "GPU_SCHEDULER_ROLE_ARN": "arn:aws:iam::123456789012:role/gpu-stop",
        "GPU_AUTO_STOP_HOURS": "3",
    }

    @patch.dict(os.environ, env, clear=True)
    def test_stopped_instance_starts_and_creates_schedule(self):
        ec2 = Mock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"State": {"Name": "stopped"}}]}]
        }
        scheduler = scheduler_mock(exists=False)

        result = wake_gpu(
            ec2_client=ec2,
            scheduler_client=scheduler,
            now=datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc),
        )

        ec2.start_instances.assert_called_once_with(InstanceIds=[self.env["GPU_INSTANCE_ID"]])
        scheduler.create_schedule.assert_called_once()
        self.assertEqual(result["state"], "pending")
        self.assertTrue(result["start_requested"])
        self.assertEqual(result["auto_stop_at"], "2026-10-15T03:00:00+00:00")

    @patch.dict(os.environ, env, clear=True)
    def test_running_instance_only_refreshes_schedule(self):
        ec2 = Mock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"State": {"Name": "running"}}]}]
        }
        scheduler = scheduler_mock(exists=True)

        result = wake_gpu(ec2_client=ec2, scheduler_client=scheduler)

        ec2.start_instances.assert_not_called()
        scheduler.update_schedule.assert_called_once()
        self.assertFalse(result["start_requested"])

    @patch.dict(os.environ, env, clear=True)
    def test_stopping_instance_requests_browser_retry(self):
        ec2 = Mock()
        ec2.describe_instances.return_value = {
            "Reservations": [{"Instances": [{"State": {"Name": "stopping"}}]}]
        }
        scheduler = scheduler_mock(exists=True)

        result = wake_gpu(ec2_client=ec2, scheduler_client=scheduler)

        self.assertEqual(result["retry_after_seconds"], 60)
        scheduler.update_schedule.assert_not_called()

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_configuration_is_rejected(self):
        with self.assertRaises(GpuLifecycleError):
            wake_gpu(ec2_client=Mock(), scheduler_client=Mock())

    @patch.dict(os.environ, {"GPU_AUTO_WAKE_ENABLED": "off"}, clear=True)
    def test_disabled_mode_does_not_call_aws(self):
        ec2 = Mock()
        scheduler = Mock()

        result = wake_gpu(ec2_client=ec2, scheduler_client=scheduler)

        self.assertEqual(result["state"], "disabled")
        self.assertFalse(result["enabled"])
        ec2.describe_instances.assert_not_called()
        scheduler.get_schedule.assert_not_called()


if __name__ == "__main__":
    unittest.main()
