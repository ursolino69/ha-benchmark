"""Frozen R3 scoring contract used by the public community ranking.

R4 is deliberately uncalibrated.  Keeping this module independent prevents an
add-on engine update from silently changing or hiding existing R3 results.
"""
import math

ENGINE_CORE_VERSION = "2026.9.1"
METHODOLOGY_ID = "CORE-2026.9.1-R3"
WEIGHTS = {
    "core_events": .20,
    "state_changes": .20,
    "entity_filter": .10,
    "entity_validation": .05,
    "json_states": .15,
    "sqlite": .20,
    "api_latency": .10,
}
STORAGE_WEIGHTS = {
    "write_mib_s": .25,
    "commit_p95_ms": .40,
    "random_read_p95_ms": .20,
    "checkpoint_ms": .15,
}
GREEN_REFERENCES = {
    "light": {
        "core_events": 49_907.0, "state_changes": 35_642.5,
        "entity_filter": 767_060.5, "entity_validation": 1_631_954.5,
        "json_states": 276_875.5,
        "sqlite": {"write_mib_s": 11.935, "commit_p95_ms": 4.1095,
                   "random_read_p95_ms": 0.4142, "checkpoint_ms": 162.92},
        "api_latency": 18.535,
    },
    "full": {
        "core_events": 49_543.0, "state_changes": 35_549.5,
        "entity_filter": 771_039.5, "entity_validation": 1_621_901.5,
        "json_states": 279_900.5,
        "sqlite": {"write_mib_s": 10.765, "commit_p95_ms": 5.3895,
                   "random_read_p95_ms": 0.28905, "checkpoint_ms": 1_657.5},
        "api_latency": 18.675,
    },
}
CALIBRATION = {
    "device": "Home Assistant Green", "index": 100,
    "calibration": "GREEN-CORE-2026-09-C", "methodology_id": METHODOLOGY_ID,
    "engine_core": ENGINE_CORE_VERSION, "core": "2026.9.1", "haos": "18.2",
    "supervisor": "2026.09.0", "sample_size": {"light": 6, "full": 6},
}


def calculate_indices(profile_name, tests):
    refs = GREEN_REFERENCES.get(profile_name)
    if not refs:
        return {}, None
    indices = {}
    for key, reference in refs.items():
        if key == "sqlite":
            result = tests[key]
            subindices = {}
            for metric, weight in STORAGE_WEIGHTS.items():
                value, ref_value = result.get(metric), reference.get(metric)
                lower_is_better = metric.endswith("_ms")
                subindices[metric] = 0 if not value or not ref_value else (
                    ref_value / value if lower_is_better else value / ref_value) * 100
            indices[key] = 0 if any(value <= 0 for value in subindices.values()) else round(
                math.exp(sum(STORAGE_WEIGHTS[m] * math.log(v) for m, v in subindices.items())))
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
    return indices, round(math.exp(sum(WEIGHTS[key] * math.log(value) for key, value in indices.items())))
