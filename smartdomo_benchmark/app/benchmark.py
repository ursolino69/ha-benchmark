from __future__ import annotations

import asyncio
import concurrent.futures
import gc
import glob
import hashlib
import json
import math
import multiprocessing
import os
import platform
import sqlite3
import statistics
import tempfile
import threading
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from device_types import infer_device_type

VERSION = "0.8.0"
ENGINE_CORE_VERSION = "2026.9.1"
METHODOLOGY_ID = "CORE-2026.9.1-R4"
API = "http://supervisor/core/api"
SUPERVISOR = "http://supervisor"


@dataclass(frozen=True)
class Profile:
    name: str
    events: int
    state_events: int
    entity_count: int
    entity_operations: int
    json_batches: int
    json_entities: int
    sqlite_payload_mib: int
    sqlite_commits: int
    sqlite_reads: int
    api_requests: int
    parallel_workers: int
    parallel_batches: int
    parallel_entities: int


PROFILES = {
    # Entity counts deliberately mirror installations with hundreds rather
    # than tens of thousands of concurrently resident entities.
    "light": Profile("light", 24_000, 12_000, 400, 40_000, 50, 400,
                     6, 100, 1_000, 10, 2, 80, 400),
    "full": Profile("full", 120_000, 60_000, 1_000, 200_000, 100, 1_000,
                    64, 1_000, 5_000, 30, 4, 180, 600),
}

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

# R4 reference medians from five controlled Green runs per profile.
GREEN_REFERENCES: dict[str, dict] = {
    "light": {
        "core_events": 33_726.0, "state_changes": 9_842.0,
        "entity_processing": 151_190.0, "json_states": 11_227.0,
        "sqlite": {"write_mib_s": 11.53, "commit_p95_ms": 4.084,
                   "random_read_p95_ms": 0.4054, "checkpoint_ms": 161.22},
        "api_latency": 18.59, "parallel_workload": 22_943.0,
    },
    "full": {
        "core_events": 34_552.0, "state_changes": 8_900.0,
        "entity_processing": 79_225.0, "json_states": 9_775.0,
        "sqlite": {"write_mib_s": 10.65, "commit_p95_ms": 5.381,
                   "random_read_p95_ms": 0.3217, "checkpoint_ms": 1_648.02},
        "api_latency": 18.88, "parallel_workload": 37_245.0,
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


class Cancelled(Exception):
    pass


def _check(cancel: Callable[[], bool]):
    if cancel():
        raise Cancelled("Benchmark abgebrochen")


def _request(path: str, method="GET", body=None, supervisor=False, timeout=10):
    token = os.environ.get("SUPERVISOR_TOKEN", "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        (SUPERVISOR if supervisor else API) + path,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
    return (json.loads(raw) if raw else None), (time.perf_counter() - started) * 1000


def _options():
    try:
        return json.loads(open("/data/options.json").read())
    except Exception:
        return {}


def pressure_info():
    """Read Linux PSI without making it part of the benchmark score."""
    result = {}
    for resource in ("cpu", "memory", "io"):
        try:
            lines = open(f"/proc/pressure/{resource}").read().splitlines()
            modes = {}
            for line in lines:
                mode, *fields = line.split()
                if mode not in ("some", "full"):
                    continue
                modes[mode] = {
                    key: float(value) if key != "total" else int(value)
                    for key, value in (field.split("=", 1) for field in fields)
                }
            if modes:
                result[resource] = modes
        except (OSError, StopIteration, ValueError):
            continue
    return result


def pressure_interval(start, end, elapsed):
    """Calculate stall-time percentages for this run from PSI total counters."""
    result = {}
    if elapsed <= 0:
        return result
    for resource in ("cpu", "memory", "io"):
        modes = {}
        for mode in ("some", "full"):
            before = start.get(resource, {}).get(mode, {}).get("total")
            after = end.get(resource, {}).get(mode, {}).get("total")
            if isinstance(before, int) and isinstance(after, int) and after >= before:
                modes[mode] = round((after - before) / (elapsed * 1_000_000) * 100, 2)
        if modes:
            result[resource] = modes
    return result


def system_info():
    memory_total = 0
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemTotal:"):
                memory_total = round(int(line.split()[1]) / 1024)
                break
    except OSError:
        pass
    cpu_model = platform.processor()
    if not cpu_model:
        try:
            fields = {}
            for line in open("/proc/cpuinfo"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    fields.setdefault(key.strip().lower(), value.strip())
            cpu_model = fields.get("model name") or fields.get("model") or fields.get("hardware")
        except OSError:
            pass
    hardware_model = ""
    for path in ("/sys/class/dmi/id/product_name", "/sys/firmware/devicetree/base/model"):
        try:
            hardware_model = open(path, "rb").read(200).replace(b"\x00", b"").decode("utf-8", "replace").strip()
            if hardware_model:
                break
        except OSError:
            continue
    info = {
        "architecture": platform.machine(), "cpu_model": cpu_model or "Unknown",
        "logical_cpus": os.cpu_count(), "memory_total_mib": memory_total,
        "platform": platform.platform(), "benchmark_engine_core": ENGINE_CORE_VERSION,
    }
    try:
        data, _ = _request("/info", supervisor=True)
        payload = data.get("data", data) if isinstance(data, dict) else {}
        info.update({key: payload.get(source) for key, source in {
            "home_assistant": "homeassistant", "supervisor": "supervisor",
            "operating_system": "operating_system", "machine": "machine"}.items()})
    except Exception:
        pass
    options = _options()
    info.update({
        "device_name": options.get("device_name") or info.get("machine") or "Unbekannt",
        "cpu_model": options.get("cpu_model") or info.get("cpu_model") or "Unbekannt",
        "storage_type": options.get("storage_type", "unknown"),
        "storage_size_gb": options.get("storage_size_gb", 0),
    })
    if hardware_model:
        info["hardware_model"] = hardware_model
    configured_type = options.get("device_type", "auto")
    if configured_type == "auto":
        try:
            configured_type = json.loads(open("/data/device.json").read()).get("device_type", "auto")
        except (OSError, ValueError, AttributeError):
            pass
    resolution = infer_device_type(info, configured_type)
    info["device_type"] = resolution.get("device_type")
    info["device_type_confidence"] = resolution.get("confidence")
    info["device_type_candidates"] = resolution.get("candidates", [])
    return info


def _run_async(coro):
    return asyncio.run(coro)


def _percentile(values, percentile):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


def core_events_test(profile, cancel):
    from homeassistant import core

    async def run():
        hass = core.HomeAssistant("")
        count = 0
        event_types = [f"smartdomo_benchmark_{index}" for index in range(8)]
        @core.callback
        def listener(_):
            nonlocal count
            count += 1
        for event_type in event_types:
            hass.bus.async_listen(event_type, listener)
        for _ in range(min(1_000, profile.events // 10)):
            hass.bus.async_fire(event_types[_ % len(event_types)], {"sequence": _, "source": "warmup"})
        await hass.async_block_till_done()
        count = 0
        started = time.perf_counter()
        for index in range(profile.events):
            hass.bus.async_fire(event_types[index % len(event_types)], {
                "sequence": index, "entity_id": f"sensor.benchmark_{index % profile.entity_count}",
                "value": index % 101,
            })
            if index and index % 1_000 == 0:
                await hass.async_block_till_done()
                _check(cancel)
        await hass.async_block_till_done()
        elapsed = time.perf_counter() - started
        await hass.async_stop()
        if count != profile.events:
            raise RuntimeError("Event-Zähler stimmt nicht überein")
        return elapsed
    elapsed = _run_async(run())
    return {"value": round(profile.events / elapsed), "unit": "Core-Events/s"}


def state_changes_test(profile, cancel):
    from homeassistant import core
    from homeassistant.const import EVENT_STATE_CHANGED
    from homeassistant.helpers.event import async_track_state_change_event

    async def run():
        hass = core.HomeAssistant("")
        count = 0
        automation_hits = 0
        @core.callback
        def listener(_):
            nonlocal count
            count += 1
        entity_ids = [f"sensor.benchmark_{i}" for i in range(profile.entity_count)]
        async_track_state_change_event(hass, entity_ids, listener)
        group_size = max(4, profile.entity_count // 50)
        for group in range(14):
            tracked = [entity_ids[(group * group_size + offset) % len(entity_ids)]
                       for offset in range(group_size)]
            @core.callback
            def automation_listener(event):
                nonlocal automation_hits
                automation_hits += 1
                # Representative condition access performed by state-based automations.
                new_state = event.data.get("new_state")
                if new_state is not None:
                    _ = new_state.state, new_state.attributes.get("sequence")
            async_track_state_change_event(hass, tracked, automation_listener)
        for _ in range(min(1_000, profile.state_events // 10)):
            entity_id = entity_ids[_ % len(entity_ids)]
            hass.bus.async_fire(EVENT_STATE_CHANGED, {
                "entity_id": entity_id,
                "old_state": core.State(entity_id, str(_ % 100), {"unit_of_measurement": "W"}),
                "new_state": core.State(entity_id, str((_ + 1) % 100), {"unit_of_measurement": "W"}),
            })
        await hass.async_block_till_done()
        count = 0
        automation_hits = 0
        started = time.perf_counter()
        for index in range(profile.state_events):
            entity_id = entity_ids[index % len(entity_ids)]
            hass.bus.async_fire(EVENT_STATE_CHANGED, {
                "entity_id": entity_id,
                "old_state": core.State(entity_id, str(index % 100), {"sequence": index - 1}),
                "new_state": core.State(entity_id, str((index + 1) % 100), {"sequence": index}),
            })
            if index and index % 500 == 0:
                await hass.async_block_till_done()
                _check(cancel)
        await hass.async_block_till_done()
        elapsed = time.perf_counter() - started
        await hass.async_stop()
        if count != profile.state_events:
            raise RuntimeError("State-Zähler stimmt nicht überein")
        return elapsed, automation_hits
    elapsed, automation_hits = _run_async(run())
    return {"value": round(profile.state_events / elapsed), "unit": "State-Events/s",
            "entities": profile.entity_count, "automation_groups": 14,
            "automation_callback_calls": automation_hits}


def entity_processing_test(profile, cancel):
    from homeassistant import core
    from homeassistant.helpers.entityfilter import convert_include_exclude_filter
    config = {"include": {"domains": ["automation", "script", "group", "media_player"], "entity_globs": ["binary_sensor.*_contact", "input_*", "switch.*_light"], "entities": ["binary_sensor.garage_door_open"]}, "exclude": {"domains": ["input_number"], "entity_globs": ["media_player.google_*"], "entities": []}}
    entity_filter = convert_include_exclude_filter(config)
    domains = ("sensor", "binary_sensor", "switch", "light", "automation", "media_player", "input_number", "person")
    entity_ids = [f"{domains[index % len(domains)]}.benchmark_{index}" for index in range(profile.entity_count)]
    started = time.perf_counter()
    accepted = 0
    for index in range(profile.entity_operations):
        # Four warm identifiers followed by one new identifier approximate a
        # mixed cache workload instead of timing a single cached dictionary hit.
        entity_id = (f"sensor.dynamic_{index}" if index % 5 == 0
                     else entity_ids[(index * 97) % len(entity_ids)])
        accepted += bool(entity_filter(entity_id))
        accepted += bool(core.valid_entity_id(entity_id))
        if index % 25_000 == 0:
            _check(cancel)
    return {"value": round(profile.entity_operations / (time.perf_counter() - started)),
            "unit": "Entity-Paare/s", "entities": profile.entity_count,
            "cache_mix": "80% wiederkehrend / 20% neu", "accepted_checks": accepted}


def json_states_test(profile, cancel):
    from homeassistant import core
    from homeassistant.helpers.json import JSON_DUMP
    gc.collect()
    total = profile.json_batches * profile.json_entities
    started = time.perf_counter()
    for batch in range(profile.json_batches):
        states = [core.State(
            f"sensor.benchmark_{index}", str((batch + index) % 1000),
            {"friendly_name": f"Benchmark {index}", "sequence": batch,
             "unit_of_measurement": "W", "available": index % 23 != 0},
        ) for index in range(profile.json_entities)]
        JSON_DUMP(states)
        if batch % 5 == 0:
            _check(cancel)
    elapsed = time.perf_counter() - started
    return {"value": round(total / elapsed), "unit": "frische States/s",
            "batches": profile.json_batches, "entities_per_batch": profile.json_entities}


def _parallel_state_worker(job):
    """Generate and serialize fresh HA states in an isolated worker process."""
    batches, entities, worker = job
    from homeassistant import core
    from homeassistant.helpers.json import JSON_DUMP
    completed = 0
    for batch in range(batches):
        states = [core.State(
            f"sensor.parallel_{worker}_{index}", str((batch + index) % 1000),
            {"worker": worker, "sequence": batch, "unit_of_measurement": "W"},
        ) for index in range(entities)]
        JSON_DUMP(states)
        completed += len(states)
    return completed


def parallel_workload_test(profile, cancel):
    workers = max(1, min(profile.parallel_workers, os.cpu_count() or 1))
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        # Import and process start-up are deliberately outside the timed region.
        list(pool.map(_parallel_state_worker, [(1, 20, worker) for worker in range(workers)]))
        _check(cancel)
        jobs = [(profile.parallel_batches, profile.parallel_entities, worker) for worker in range(workers)]
        started = time.perf_counter()
        completed = sum(pool.map(_parallel_state_worker, jobs))
        elapsed = time.perf_counter() - started
    _check(cancel)
    return {"value": round(completed / elapsed), "unit": "parallele States/s",
            "workers": workers, "states": completed,
            "entities_per_batch": profile.parallel_entities}


def sqlite_test(profile, cancel):
    path = None
    db = None
    try:
        with tempfile.NamedTemporaryFile(prefix="smartdomo-sqlite-", suffix=".db", dir="/data", delete=False) as f:
            path = f.name
        db = sqlite3.connect(path)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA wal_autocheckpoint=0")
        db.execute("PRAGMA temp_store=MEMORY")
        db.execute("CREATE TABLE states (id INTEGER PRIMARY KEY, entity_id TEXT, state TEXT, attributes BLOB, updated REAL)")
        db.execute("CREATE INDEX idx_states_entity_updated ON states(entity_id, updated)")

        payload = bytes((index % 251 for index in range(2_048)))
        row_count = profile.sqlite_payload_mib * 1_048_576 // len(payload)
        rows_per_commit, extra_rows = divmod(row_count, profile.sqlite_commits)
        commit_times = []
        row_id = 0
        write_started = time.perf_counter()
        for commit_index in range(profile.sqlite_commits):
            _check(cancel)
            db.execute("BEGIN IMMEDIATE")
            rows_this_commit = rows_per_commit + (1 if commit_index < extra_rows else 0)
            for _ in range(rows_this_commit):
                row_id += 1
                db.execute(
                    "INSERT INTO states(entity_id,state,attributes,updated) VALUES(?,?,?,?)",
                    (f"sensor.benchmark_{row_id % 500}", str(row_id), payload, float(row_id)),
                )
            commit_started = time.perf_counter()
            db.commit()
            commit_times.append((time.perf_counter() - commit_started) * 1_000)
        write_elapsed = time.perf_counter() - write_started

        _check(cancel)
        peak_temporary_mib = sum(
            os.path.getsize(path + suffix)
            for suffix in ("", "-wal", "-shm")
            if os.path.exists(path + suffix)
        ) / 1_048_576
        checkpoint_started = time.perf_counter()
        checkpoint_result = db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        checkpoint_ms = (time.perf_counter() - checkpoint_started) * 1_000
        db.close()
        db = None

        cache_drop_requested = False
        file_descriptor = os.open(path, os.O_RDONLY)
        try:
            try:
                os.fsync(file_descriptor)
            except OSError:
                pass
            if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED"):
                try:
                    os.posix_fadvise(file_descriptor, 0, 0, os.POSIX_FADV_DONTNEED)
                    cache_drop_requested = True
                except OSError:
                    pass
        finally:
            os.close(file_descriptor)

        db = sqlite3.connect(path)
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA mmap_size=0")
        db.execute("PRAGMA cache_size=-1024")
        read_times = []
        read_started = time.perf_counter()
        for index in range(profile.sqlite_reads):
            if index % 500 == 0:
                _check(cancel)
            selected_id = (index * 7_919) % row_count + 1
            operation_started = time.perf_counter_ns()
            db.execute("SELECT state, attributes FROM states WHERE id=?", (selected_id,)).fetchone()
            read_times.append((time.perf_counter_ns() - operation_started) / 1_000_000)
        read_elapsed = time.perf_counter() - read_started
        db.close()
        db = None

        commit_p95 = _percentile(commit_times, .95)
        read_p95 = _percentile(read_times, .95)
        return {
            "value": round(commit_p95, 3),
            "unit": "ms Commit-p95",
            "write_mib_s": round(profile.sqlite_payload_mib / write_elapsed, 2),
            "commit_median_ms": round(statistics.median(commit_times), 3),
            "commit_p95_ms": round(commit_p95, 3),
            "commit_p99_ms": round(_percentile(commit_times, .99), 3),
            "random_read_median_ms": round(statistics.median(read_times), 4),
            "random_read_p95_ms": round(read_p95, 4),
            "random_read_p99_ms": round(_percentile(read_times, .99), 4),
            "random_reads_s": round(profile.sqlite_reads / read_elapsed),
            "checkpoint_ms": round(checkpoint_ms, 2),
            "checkpoint_busy": checkpoint_result[0] if checkpoint_result else None,
            "database_size_mib": round(os.path.getsize(path) / 1_048_576, 2),
            "peak_temporary_mib": round(peak_temporary_mib, 2),
            "payload_mib": profile.sqlite_payload_mib,
            "rows": row_count,
            "commits": profile.sqlite_commits,
            "reads": profile.sqlite_reads,
            "cache_drop_requested": cache_drop_requested,
        }
    finally:
        if db is not None:
            db.close()
        if path:
            for suffix in ("", "-wal", "-shm", "-journal"):
                try:
                    os.unlink(path + suffix)
                except FileNotFoundError:
                    pass


def api_latency_test(profile, cancel):
    times = []
    for _ in range(profile.api_requests):
        _check(cancel)
        _, elapsed = _request("/", timeout=5)
        times.append(elapsed)
    return {"value": round(statistics.median(times), 2), "unit": "ms Median", "p95_ms": round(sorted(times)[max(0, math.ceil(len(times) * .95) - 1)], 2)}


TESTS = [
    ("core_events", "Core Events", core_events_test),
    ("state_changes", "State Changes", state_changes_test),
    ("entity_processing", "Entity-Verarbeitung", entity_processing_test),
    ("json_states", "JSON States", json_states_test),
    ("sqlite", "SQLite Recorder", sqlite_test),
    ("api_latency", "HA API", api_latency_test),
    ("parallel_workload", "Parallele Last", parallel_workload_test),
]


class EnvironmentSampler:
    def __init__(self, cancel):
        options = _options()
        self.temperature_entity = options.get("temperature_entity", "").strip()
        self.power_entity = options.get("power_entity", "").strip()
        self.temperature_path = self._find_temperature_path()
        self.cancel = cancel
        self.samples = []
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.temperature_entity or self.temperature_path or self.power_entity:
            self.thread = threading.Thread(target=self._sample, daemon=True)
            self.thread.start()

    @staticmethod
    def _find_temperature_path():
        candidates = []
        for path in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
            try:
                zone_type = open(os.path.join(os.path.dirname(path), "type")).read().strip().lower()
                raw = float(open(path).read().strip())
                value = raw / 1000 if raw > 1000 else raw
                if 0 < value < 150:
                    priority = 0 if any(name in zone_type for name in ("cpu", "soc", "package", "rk")) else 1
                    candidates.append((priority, path))
            except (OSError, ValueError):
                continue
        return min(candidates)[1] if candidates else None

    def _read_system_temperature(self):
        if not self.temperature_path:
            return None
        try:
            raw = float(open(self.temperature_path).read().strip())
            value = raw / 1000 if raw > 1000 else raw
            return value if 0 < value < 150 else None
        except (OSError, ValueError):
            return None

    def _read_entity(self, entity_id):
        if not entity_id:
            return None, None
        try:
            data, _ = _request(f"/states/{entity_id}", timeout=3)
            return float(data["state"]), data.get("attributes", {}).get("unit_of_measurement")
        except Exception:
            return None, None

    def _sample(self):
        while not self.stop_event.is_set():
            temp, temp_unit = self._read_entity(self.temperature_entity)
            temp_source = "home_assistant_entity" if temp is not None else None
            if temp is None:
                temp = self._read_system_temperature()
                temp_unit = "°C" if temp is not None else None
                temp_source = "sysfs" if temp is not None else None
            power, power_unit = self._read_entity(self.power_entity)
            if power is not None and power_unit == "kW":
                power *= 1000
                power_unit = "W"
            self.samples.append({"time": time.time(), "temperature": temp, "temperature_unit": temp_unit, "temperature_source": temp_source, "power_w": power if power_unit in ("W", None) else None})
            self.stop_event.wait(1)

    def finish(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=4)
        temps = [s["temperature"] for s in self.samples if s["temperature"] is not None]
        powers = [s for s in self.samples if s["power_w"] is not None]
        result = {"samples": len(self.samples)}
        if temps:
            result["temperature"] = {"start": round(temps[0], 1), "maximum": round(max(temps), 1), "delta": round(max(temps) - temps[0], 1), "unit": next((s["temperature_unit"] for s in self.samples if s["temperature_unit"]), "°C"), "source": next((s["temperature_source"] for s in self.samples if s["temperature_source"]), None)}
        if powers:
            watts = [s["power_w"] for s in powers]
            watt_seconds = sum((powers[i]["power_w"] + powers[i-1]["power_w"]) / 2 * (powers[i]["time"] - powers[i-1]["time"]) for i in range(1, len(powers)))
            result["energy"] = {"average_w": round(statistics.mean(watts), 2), "peak_w": round(max(watts), 2), "consumption_wh": round(watt_seconds / 3600, 4)}
        return result


def calculate_indices(profile_name, tests):
    refs = GREEN_REFERENCES.get(profile_name)
    if not refs:
        return {}, None
    indices = {}
    for key, reference in refs.items():
        if key == "sqlite" and isinstance(reference, dict):
            result = tests[key]
            if result.get("error"):
                indices[key] = 0
                continue
            subindices = {}
            for metric, weight in STORAGE_WEIGHTS.items():
                value = result.get(metric)
                ref_value = reference.get(metric)
                lower_is_better = metric.endswith("_ms")
                subindices[metric] = 0 if not value or not ref_value else (ref_value / value if lower_is_better else value / ref_value) * 100
            indices[key] = 0 if any(value <= 0 for value in subindices.values()) else round(math.exp(sum(STORAGE_WEIGHTS[metric] * math.log(value) for metric, value in subindices.items())))
            result["subindices"] = {metric: round(value) for metric, value in subindices.items()}
            result["index"] = indices[key]
            result["green_reference"] = reference
            continue
        value = tests[key].get("value")
        indices[key] = 0 if not value or tests[key].get("error") else round((reference / value if key == "api_latency" else value / reference) * 100)
        tests[key]["index"] = indices[key]
        tests[key]["green_reference"] = reference
    if any(value <= 0 for value in indices.values()):
        return indices, 0
    return indices, round(math.exp(sum(WEIGHTS[key] * math.log(value) for key, value in indices.items())))


def run_benchmark(profile_name, progress, cancel):
    profile = PROFILES[profile_name]
    result = {"schema_version": 2, "benchmark_version": VERSION, "methodology_id": METHODOLOGY_ID, "engine_core_version": ENGINE_CORE_VERSION, "profile": profile_name, "started_at": datetime.now(timezone.utc).isoformat(), "system": system_info(), "weights": WEIGHTS, "tests": {}}
    pressure_start = pressure_info()
    sampler = EnvironmentSampler(cancel)
    sampler.start()
    started = time.perf_counter()
    try:
        for index, (key, label, test) in enumerate(TESTS):
            _check(cancel)
            progress(index / len(TESTS), label)
            try:
                result["tests"][key] = test(profile, cancel)
            except Cancelled:
                raise
            except Exception as exc:
                result["tests"][key] = {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        result["environment"] = sampler.finish()
        pressure_end = pressure_info()
        if pressure_start or pressure_end:
            elapsed = time.perf_counter() - started
            result["environment"]["pressure"] = {
                "start": pressure_start,
                "end": pressure_end,
                "interval_percent": pressure_interval(pressure_start, pressure_end, elapsed),
            }
    indices, overall = calculate_indices(profile_name, result["tests"])
    result.update({"indices": indices, "index": overall, "score": overall, "calibration_status": "pending" if overall is None else "calibrated", "duration_seconds": round(time.perf_counter() - started, 2), "finished_at": datetime.now(timezone.utc).isoformat()})
    if overall is not None and CALIBRATION:
        result["reference"] = CALIBRATION
    result["result_id"] = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:12]
    progress(1, "Fertig")
    return result
