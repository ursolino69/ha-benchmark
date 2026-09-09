from __future__ import annotations

import csv
import io
import json
import os
import threading
import logging
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from benchmark import Cancelled, run_benchmark, system_info
from sharing import COMMUNITY, make_payload

ROOT = Path(__file__).parent
DATA = Path("/data")
RESULTS = DATA / "results.json"
OPTIONS = DATA / "options.json"
lock = threading.Lock()
state = {"running": False, "progress": 0, "stage": "Bereit", "error": None, "latest": None, "cancel": False}
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger('benchmark')
share_lock = threading.Lock()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def shared_records():
    try:
        return json.loads((DATA / 'shared.json').read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def community_post(payload):
    request = urllib.request.Request(COMMUNITY + '/api/entries', data=json.dumps(dict(payload, consent=True)).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
            reply = json.loads(response.read(65536))
            if (not isinstance(reply, dict) or not isinstance(reply.get('id'), str)
                    or not isinstance(reply.get('url'), str) or not isinstance(reply.get('delete_key'), str)):
                raise ValueError('Invalid community response / Ungültige Community-Antwort')
            return reply
    except urllib.error.HTTPError as exc:
        raise ValueError(json.loads(exc.read(4096)).get('error', 'Community request failed')) from None
    except (urllib.error.URLError, TimeoutError):
        raise ValueError('Community unreachable / Community nicht erreichbar') from None


def load_results():
    try:
        return json.loads(RESULTS.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_result(result):
    results = load_results()
    results.insert(0, result)
    RESULTS.write_text(json.dumps(results[:50], indent=2))


def full_allowed():
    try:
        return bool(json.loads(OPTIONS.read_text()).get("allow_full_benchmark", False))
    except Exception:
        return False


def worker(profile):
    LOG.info('benchmark_start profile=%s', profile)
    def progress(value, stage):
        LOG.info('benchmark_stage progress=%s', round(value * 100))
        with lock:
            state.update(progress=round(value * 100), stage=stage)
    try:
        result = run_benchmark(profile, progress, lambda: state["cancel"])
        save_result(result)
        LOG.info('benchmark_complete profile=%s index=%s duration=%s', profile, result.get('index'), result.get('duration_seconds'))
        for name, test in result.get('tests', {}).items():
            if test.get('error'):
                LOG.warning('benchmark_category_failed category=%s', name)
        with lock:
            state.update(latest=result, running=False, error=None, cancel=False)
    except Cancelled:
        LOG.info('benchmark_cancelled')
        with lock:
            state.update(running=False, stage="Abgebrochen", cancel=False)
    except Exception as exc:
        LOG.error('benchmark_failed type=%s', type(exc).__name__)
        with lock:
            state.update(running=False, error=str(exc), stage="Fehler", cancel=False)


class Handler(BaseHTTPRequestHandler):
    def trusted(self):
        return self.client_address[0] in ('172.30.32.2', '127.0.0.1', '::1')

    def send_json(self, payload, status=200):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if not self.trusted():
            return self.send_json({'error':'Ingress only'}, 403)
        path = urlparse(self.path).path.rstrip("/")
        if path.endswith("/api/status"):
            with lock:
                self.send_json(dict(state, full_allowed=full_allowed()))
        elif path.endswith("/api/results"):
            self.send_json(load_results())
        elif path.endswith('/api/shared'):
            self.send_json(shared_records())
        elif path.endswith("/api/system"):
            self.send_json(system_info())
        elif path.endswith("/api/export.csv"):
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "result_id", "date", "version", "methodology_id", "engine_core", "profile", "index",
                "duration_s", "device", "machine", "cpu", "ram_mib", "storage_type", "storage_gb",
                "haos", "ha_core", "supervisor", "core_events", "state_changes", "entity_filter",
                "entity_validation", "json_states", "storage_write_mib_s", "storage_commit_median_ms",
                "storage_commit_p95_ms", "storage_commit_p99_ms", "storage_random_read_median_ms",
                "storage_random_read_p95_ms", "storage_random_read_p99_ms", "storage_random_reads_s",
                "storage_checkpoint_ms", "storage_database_mib", "storage_payload_mib", "storage_commits",
                "storage_peak_temporary_mib", "storage_cache_drop_requested", "api_latency_ms",
                "temperature_start", "temperature_max", "power_average_w", "power_peak_w", "energy_wh",
                "psi_cpu_avg10", "psi_memory_avg10", "psi_io_avg10",
            ])
            for r in load_results():
                s, tests, env = r.get("system", {}), r.get("tests", {}), r.get("environment", {})
                temp, energy = env.get("temperature", {}), env.get("energy", {})
                pressure = env.get("pressure", {}).get("end", {})
                value = lambda key: tests.get(key, {}).get("value")
                storage = tests.get("sqlite", {})
                writer.writerow([
                    r.get("result_id"), r.get("finished_at"), r.get("benchmark_version"),
                    r.get("methodology_id"), r.get("engine_core_version"), r.get("profile"),
                    r.get("index"), r.get("duration_seconds"), s.get("device_name"), s.get("machine"),
                    s.get("cpu_model"), s.get("memory_total_mib"), s.get("storage_type"),
                    s.get("storage_size_gb"), s.get("operating_system"), s.get("home_assistant"),
                    s.get("supervisor"), value("core_events"), value("state_changes"),
                    value("entity_filter"), value("entity_validation"), value("json_states"),
                    storage.get("write_mib_s"), storage.get("commit_median_ms"),
                    storage.get("commit_p95_ms"), storage.get("commit_p99_ms"),
                    storage.get("random_read_median_ms"), storage.get("random_read_p95_ms"),
                    storage.get("random_read_p99_ms"), storage.get("random_reads_s"),
                    storage.get("checkpoint_ms"), storage.get("database_size_mib"),
                    storage.get("payload_mib"), storage.get("commits"),
                    storage.get("peak_temporary_mib"), storage.get("cache_drop_requested"),
                    value("api_latency"), temp.get("start"), temp.get("maximum"),
                    energy.get("average_w"), energy.get("peak_w"), energy.get("consumption_wh"),
                    pressure.get("cpu", {}).get("avg10"), pressure.get("memory", {}).get("avg10"),
                    pressure.get("io", {}).get("avg10"),
                ])
            raw = output.getvalue().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=smartdomo-ha-benchmark.csv")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif path.endswith("/api/export.json"):
            self.send_json(load_results())
        else:
            name = path.split('/')[-1]
            allowed = {'ui.js':'text/javascript', 'style.css':'text/css', 'brand.png':'image/png',
                       'methodology.html':'text/html', 'methodology.js':'text/javascript'}
            raw = (ROOT / (name if name in allowed else 'index.html')).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", allowed.get(name, 'text/html'))
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    def do_POST(self):
        if not self.trusted() or self.headers.get('X-Benchmark-Request') != '1':
            return self.send_json({'error':'Invalid request'}, 403)
        path = urlparse(self.path).path.rstrip("/")
        if path.endswith('/api/share-preview') or path.endswith('/api/share'):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 8192:
                    raise ValueError('Invalid request size')
                body = json.loads(self.rfile.read(size))
                ids = body.get('ids', [])
                if not isinstance(ids, list) or len(ids) not in (1,3) or len(set(ids)) != len(ids):
                    raise ValueError('Select one or three runs / Einen oder drei Läufe wählen')
                saved = {r['result_id']:r for r in load_results()}
                if any(rid not in saved for rid in ids):
                    raise ValueError('Result not found')
                payload = make_payload([saved[rid] for rid in ids], body.get('alias',''), body.get('device_model',''), body.get('include_environment') is True)
                if path.endswith('/api/share-preview'):
                    return self.send_json(payload)
                if body.get('consent') is not True:
                    raise ValueError('Consent required')
                with share_lock:
                    reply = community_post(payload)
                    # Save the private key before returning it to the UI.
                    records = shared_records()
                    records.insert(0, reply)
                    tmp = DATA / 'shared.json.tmp'
                    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                    with os.fdopen(fd, 'w') as handle:
                        json.dump(records, handle)
                    tmp.replace(DATA / 'shared.json')
                LOG.info('community_published id=%s', reply.get('id'))
                return self.send_json(reply, 201)
            except (ValueError, TypeError, KeyError) as exc:
                return self.send_json({'error':str(exc)}, 400)
            except Exception:
                LOG.error('community_share_failed')
                return self.send_json({'error':'Sharing failed / Teilen fehlgeschlagen'}, 503)
        if path.endswith("/api/run"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                profile = json.loads(self.rfile.read(length) or b"{}").get("profile", "light")
            except Exception:
                return self.send_json({"error": "Ungültige Anfrage"}, 400)
            if profile not in ("light", "full"):
                return self.send_json({"error": "Unbekanntes Profil"}, 400)
            if profile == "full" and not full_allowed():
                return self.send_json({"error": "Full-Benchmark ist in der App-Konfiguration nicht freigeschaltet."}, 403)
            with lock:
                if state["running"]:
                    return self.send_json({"error": "Benchmark läuft bereits"}, 409)
                state.update(running=True, progress=0, stage="Vorbereitung", error=None, cancel=False)
            threading.Thread(target=worker, args=(profile,), daemon=True).start()
            self.send_json({"started": True, "profile": profile}, 202)
        elif path.endswith("/api/cancel"):
            with lock:
                state["cancel"] = True
            self.send_json({"cancel_requested": True})
        else:
            self.send_json({"error": "Nicht gefunden"}, 404)

    def log_message(self, fmt, *args):
        # Do not log paths, query strings, client addresses or private keys.
        pass


if __name__ == "__main__":
    LOG.info('HA Benchmark 0.5.0 starting; R3; community upload only after consent')
    DATA.mkdir(exist_ok=True)
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
