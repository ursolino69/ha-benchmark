import copy
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).parents[1] / "smartdomo_benchmark" / "app"
sys.path.insert(0, str(APP))
import benchmark
import sharing
import device_types


def run(number=1, multiplier=1.0):
    references = benchmark.GREEN_REFERENCES["light"]
    tests = {}
    for key, value in references.items():
        if key == "sqlite":
            tests[key] = {name: raw * multiplier for name, raw in value.items()}
        else:
            tests[key] = {"value": value * multiplier}
    return {
        "result_id": f"{number:012x}",
        "benchmark_version": "0.5.0",
        "methodology_id": benchmark.METHODOLOGY_ID,
        "engine_core_version": benchmark.ENGINE_CORE_VERSION,
        "reference": benchmark.CALIBRATION,
        "profile": "light",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": 3.5,
        "system": {
            "architecture": "aarch64", "cpu_model": "RK3566", "logical_cpus": 4,
            "memory_total_mib": 4096, "home_assistant": "2026.9.1",
            "operating_system": "Home Assistant OS 18.2", "supervisor": "2026.09.0",
            "machine": "green", "storage_type": "emmc", "storage_size_gb": 32,
            "device_name": "Private kitchen Green", "platform": "private-host.example",
        },
        "tests": tests,
        "environment": {"temperature": {"start": 40, "maximum": 44}, "energy": {"average_w": 3}},
    }


class SharingTests(unittest.TestCase):
    def test_private_fields_are_removed(self):
        payload = sharing.make_payload([run()], "Alias", "Home Assistant Green", True)
        public = payload["runs"][0]
        self.assertNotIn("device_name", public["system"])
        self.assertNotIn("platform", public["system"])
        self.assertNotIn("pressure", public.get("environment", {}))
        self.assertEqual(payload["device_model"], "Home Assistant Green")

    def test_green_reference_summarizes_to_100(self):
        payload = sharing.make_payload([run()], "", "Home Assistant Green")
        summary = sharing.summarize(payload)
        self.assertEqual(summary["index"], 100)
        self.assertTrue(all(value == 100 for value in summary["indices"].values()))

    def test_three_run_overall_is_median(self):
        runs = [run(1, .9), run(2, 1), run(3, 1.1)]
        runs[0]["environment"]["temperature"]["maximum"] = 42
        runs[1]["environment"]["temperature"]["maximum"] = 44
        runs[2]["environment"]["temperature"]["maximum"] = 50
        payload = sharing.make_payload(runs, "", "Green", True)
        summary = sharing.summarize(payload)
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["index"], 100)
        self.assertEqual(summary["environment"]["temperature"]["maximum"], 44)
        self.assertEqual(summary["quality"]["level"], "moderate")
        self.assertEqual(summary["quality"]["runs"], 3)

    def test_stable_three_run_quality(self):
        payload = sharing.make_payload([run(11, .99), run(12, 1), run(13, 1.01)], "", "Green")
        self.assertEqual(sharing.summarize(payload)["quality"]["level"], "stable")

    def test_device_detection_is_conservative(self):
        pi = device_types.infer_device_type({"machine": "raspberrypi5-64", "architecture": "aarch64"})
        self.assertEqual(pi["device_type"], "rpi5")
        avatto = device_types.infer_device_type({"machine": "green", "architecture": "aarch64",
                                                "memory_total_mib": 7952, "cpu_model": "RK3566"})
        self.assertIsNone(avatto["device_type"])
        self.assertIn("green", avatto["candidates"])
        self.assertIn("avatto_ha80", avatto["candidates"])
        named = device_types.infer_device_type({"machine": "green", "architecture": "aarch64",
                                                "memory_total_mib": 7952, "cpu_model": "RK3566"},
                                               device_model="Avatto HA80")
        self.assertEqual(named["device_type"], "avatto_ha80")

    def test_three_runs_must_match_system(self):
        changed = run(3)
        changed["system"]["storage_type"] = "sd"
        with self.assertRaises(ValueError):
            sharing.make_payload([run(1), run(2), changed], "", "Green")

    def test_invalid_or_failed_measurement_is_rejected(self):
        bad = copy.deepcopy(run())
        bad["tests"]["core_events"]["error"] = "failed"
        with self.assertRaises(ValueError):
            sharing.make_payload([bad], "", "Green")

    def test_control_characters_and_storage_values_are_rejected(self):
        with self.assertRaises(ValueError):
            sharing.make_payload([run()], "Lab\u202e", "Green")
        bad = run()
        bad["system"]["storage_type"] = "magic"
        with self.assertRaises(ValueError):
            sharing.make_payload([bad], "", "Green")


if __name__ == "__main__":
    unittest.main()
