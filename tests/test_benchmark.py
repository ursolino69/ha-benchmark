import sys
import time
import types
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "smartdomo_benchmark" / "app"))
import benchmark


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.references = {
            "core_events": 1000,
            "state_changes": 900,
            "entity_filter": 800,
            "entity_validation": 700,
            "json_states": 600,
            "sqlite": 500,
            "api_latency": 10,
        }

    def test_weights_are_complete_and_sum_to_one(self):
        self.assertEqual(set(benchmark.WEIGHTS), {key for key, _, _ in benchmark.TESTS})
        self.assertAlmostEqual(sum(benchmark.WEIGHTS.values()), 1.0)

    def test_calibration_candidate_metadata(self):
        self.assertEqual(benchmark.VERSION, "0.6.0")
        self.assertEqual(benchmark.METHODOLOGY_ID, "CORE-2026.9.1-R3")
        self.assertEqual(set(benchmark.GREEN_REFERENCES), {"light", "full"})
        self.assertEqual(benchmark.CALIBRATION["calibration"], "GREEN-CORE-2026-09-C")

    def test_built_in_green_references_produce_index_100(self):
        for profile, references in benchmark.GREEN_REFERENCES.items():
            tests = {}
            for key, reference in references.items():
                tests[key] = dict(reference) if isinstance(reference, dict) else {"value": reference}
            indices, overall = benchmark.calculate_indices(profile, tests)
            self.assertEqual(overall, 100)
            self.assertTrue(all(value == 100 for value in indices.values()))

    def test_storage_subindices_produce_index_100(self):
        storage = {
            "write_mib_s": 10,
            "commit_p95_ms": 5,
            "random_read_p95_ms": 1,
            "checkpoint_ms": 20,
        }
        references = dict(self.references)
        references["sqlite"] = storage
        tests = {key: {"value": value} for key, value in self.references.items()}
        tests["sqlite"].update(storage)
        original = benchmark.GREEN_REFERENCES
        try:
            benchmark.GREEN_REFERENCES = {"light": references}
            indices, overall = benchmark.calculate_indices("light", tests)
        finally:
            benchmark.GREEN_REFERENCES = original
        self.assertEqual(indices["sqlite"], 100)
        self.assertEqual(overall, 100)
        self.assertTrue(all(value == 100 for value in tests["sqlite"]["subindices"].values()))

    def test_storage_index_uses_correct_metric_directions(self):
        storage_reference = {
            "write_mib_s": 10,
            "commit_p95_ms": 5,
            "random_read_p95_ms": 1,
            "checkpoint_ms": 20,
        }
        references = dict(self.references)
        references["sqlite"] = storage_reference
        tests = {key: {"value": value} for key, value in self.references.items()}
        tests["sqlite"].update({
            "write_mib_s": 20,
            "commit_p95_ms": 2.5,
            "random_read_p95_ms": .5,
            "checkpoint_ms": 10,
        })
        original = benchmark.GREEN_REFERENCES
        try:
            benchmark.GREEN_REFERENCES = {"light": references}
            indices, _ = benchmark.calculate_indices("light", tests)
        finally:
            benchmark.GREEN_REFERENCES = original
        self.assertEqual(indices["sqlite"], 200)

    def test_event_rate_includes_event_creation(self):
        class FakeBus:
            def async_listen(self, _event_name, listener):
                self.listener = listener

            def async_fire(self, _event_name):
                time.sleep(0.0005)
                self.listener(None)

        class FakeHomeAssistant:
            def __init__(self, _config_dir):
                self.bus = FakeBus()

            async def async_block_till_done(self):
                return None

            async def async_stop(self):
                return None

        fake_core = types.ModuleType("homeassistant.core")
        fake_core.HomeAssistant = FakeHomeAssistant
        fake_core.callback = lambda function: function
        fake_homeassistant = types.ModuleType("homeassistant")
        fake_homeassistant.core = fake_core
        with patch.dict(sys.modules, {"homeassistant": fake_homeassistant, "homeassistant.core": fake_core}):
            result = benchmark.core_events_test(SimpleNamespace(events=20), lambda: False)
        self.assertLess(result["value"], 10_000)

    def test_full_profile_is_larger_than_light(self):
        light = benchmark.PROFILES["light"]
        full = benchmark.PROFILES["full"]
        for field in (
            "events", "state_events", "listeners", "filter_calls",
            "validation_calls", "json_states", "sqlite_payload_mib",
            "sqlite_commits", "sqlite_reads", "api_requests",
        ):
            self.assertGreater(getattr(full, field), getattr(light, field))

    def test_storage_test_reports_durable_latency_metrics(self):
        original = benchmark.tempfile.NamedTemporaryFile
        with tempfile.TemporaryDirectory() as directory:
            def temporary_file(**kwargs):
                kwargs["dir"] = directory
                return original(**kwargs)
            profile = SimpleNamespace(sqlite_payload_mib=1, sqlite_commits=10, sqlite_reads=50)
            with patch.object(benchmark.tempfile, "NamedTemporaryFile", temporary_file):
                result = benchmark.sqlite_test(profile, lambda: False)
        for key in (
            "write_mib_s", "commit_p95_ms", "random_read_p95_ms",
            "checkpoint_ms", "database_size_mib", "peak_temporary_mib",
        ):
            self.assertGreater(result[key], 0)
        self.assertEqual(result["commits"], 10)
        self.assertEqual(result["reads"], 50)

    def test_unknown_profile_returns_no_index(self):
        tests = {key: {"value": value} for key, value in self.references.items()}
        indices, overall = benchmark.calculate_indices("future-profile", tests)
        self.assertEqual(indices, {})
        self.assertIsNone(overall)

    def test_reference_values_produce_green_index_100(self):
        original = benchmark.GREEN_REFERENCES
        try:
            benchmark.GREEN_REFERENCES = {"light": self.references}
            tests = {key: {"value": value} for key, value in self.references.items()}
            indices, overall = benchmark.calculate_indices("light", tests)
        finally:
            benchmark.GREEN_REFERENCES = original
        self.assertEqual(overall, 100)
        self.assertTrue(all(value == 100 for value in indices.values()))

    def test_lower_api_latency_is_better(self):
        original = benchmark.GREEN_REFERENCES
        try:
            benchmark.GREEN_REFERENCES = {"light": self.references}
            tests = {key: {"value": value} for key, value in self.references.items()}
            tests["api_latency"]["value"] = 5
            indices, _ = benchmark.calculate_indices("light", tests)
        finally:
            benchmark.GREEN_REFERENCES = original
        self.assertEqual(indices["api_latency"], 200)


if __name__ == "__main__":
    unittest.main()
