"""Frozen R4 scoring contract shared by the app and community service."""
import math

ENGINE_CORE_VERSION = "2026.9.1"
METHODOLOGY_ID = "CORE-2026.9.1-R4"
WEIGHTS = {
    "core_events": .15,
    "state_changes": .20,
    "entity_processing": .05,
    "json_states": .10,
    "sqlite": .20,
    "api_latency": .10,
    "parallel_workload": .20,
}
STORAGE_WEIGHTS = {
    "write_mib_s": .25,
    "commit_p95_ms": .40,
    "random_read_p95_ms": .20,
    "checkpoint_ms": .15,
}
GREEN_REFERENCES = {
    "light": {
        "core_events": 33_726.0,
        "state_changes": 9_842.0,
        "entity_processing": 151_190.0,
        "json_states": 11_227.0,
        "sqlite": {
            "write_mib_s": 11.53,
            "commit_p95_ms": 4.084,
            "random_read_p95_ms": 0.4054,
            "checkpoint_ms": 161.22,
        },
        "api_latency": 18.59,
        "parallel_workload": 22_943.0,
    },
    "full": {
        "core_events": 34_552.0,
        "state_changes": 8_900.0,
        "entity_processing": 79_225.0,
        "json_states": 9_775.0,
        "sqlite": {
            "write_mib_s": 10.65,
            "commit_p95_ms": 5.381,
            "random_read_p95_ms": 0.3217,
            "checkpoint_ms": 1_648.02,
        },
        "api_latency": 18.88,
        "parallel_workload": 37_245.0,
    },
}
CALIBRATION = {
    "device": "Home Assistant Green",
    "index": 100,
    "calibration": "GREEN-CORE-2026-09-D",
    "methodology_id": METHODOLOGY_ID,
    "engine_core": ENGINE_CORE_VERSION,
    "core": "2026.9.1",
    "haos": "18.2",
    "supervisor": "2026.09.0",
    "sample_size": {"light": 5, "full": 5},
    "status": "calibrated",
}


def calculate_indices(profile_name, tests):
    refs = GREEN_REFERENCES.get(profile_name)
    if not refs:
        return {}, None
    indices = {}
    for key, reference in refs.items():
        if key == "sqlite":
            result = tests[key]
            if result.get("error"):
                indices[key] = 0
                continue
            subindices = {}
            for metric in STORAGE_WEIGHTS:
                value, ref_value = result.get(metric), reference.get(metric)
                lower_is_better = metric.endswith("_ms")
                subindices[metric] = 0 if not value or not ref_value else (
                    ref_value / value if lower_is_better else value / ref_value
                ) * 100
            indices[key] = 0 if any(value <= 0 for value in subindices.values()) else round(
                math.exp(sum(STORAGE_WEIGHTS[metric] * math.log(value)
                             for metric, value in subindices.items())))
            result["subindices"] = {metric: round(value) for metric, value in subindices.items()}
            result["index"] = indices[key]
            result["green_reference"] = reference
            continue
        value = tests[key].get("value")
        indices[key] = 0 if not value or tests[key].get("error") else round(
            (reference / value if key == "api_latency" else value / reference) * 100)
        tests[key]["index"] = indices[key]
        tests[key]["green_reference"] = reference
    if any(value <= 0 for value in indices.values()):
        return indices, 0
    return indices, round(math.exp(sum(WEIGHTS[key] * math.log(value)
                                       for key, value in indices.items())))
