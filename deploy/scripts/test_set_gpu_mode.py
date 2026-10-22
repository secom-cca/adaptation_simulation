import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("set_gpu_mode.py")
SPEC = importlib.util.spec_from_file_location("set_gpu_mode", MODULE_PATH)
set_gpu_mode = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(set_gpu_mode)


class SetGpuModeTest(unittest.TestCase):
    def test_replaces_only_selected_environment_variables(self):
        task = {
            "family": "adaptation-web",
            "containerDefinitions": [{
                "name": "web",
                "environment": [
                    {"name": "ADMIN_EXPORT_TOKEN", "value": "preserved"},
                    {"name": "OLLAMA_HOST", "value": "old"},
                ],
            }],
        }

        updated = set_gpu_mode._replace_environment(
            task,
            {"OLLAMA_HOST": "http://127.0.0.1:11434", "GPU_AUTO_WAKE_ENABLED": "false"},
        )
        environment = {
            item["name"]: item["value"]
            for item in updated["containerDefinitions"][0]["environment"]
        }

        self.assertEqual(environment["ADMIN_EXPORT_TOKEN"], "preserved")
        self.assertEqual(environment["OLLAMA_HOST"], "http://127.0.0.1:11434")
        self.assertEqual(environment["GPU_AUTO_WAKE_ENABLED"], "false")
        self.assertEqual(task["containerDefinitions"][0]["environment"][1]["value"], "old")

    def test_registration_payload_removes_read_only_fields(self):
        task = {
            "family": "adaptation-web",
            "containerDefinitions": [],
            "taskDefinitionArn": "arn:read-only",
            "revision": 9,
            "status": "ACTIVE",
        }

        payload = set_gpu_mode._registration_payload(task)

        self.assertEqual(payload, {"family": "adaptation-web", "containerDefinitions": []})


if __name__ == "__main__":
    unittest.main()
