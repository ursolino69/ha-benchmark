"""Public data contract, shared by the add-on and the ranking server."""
import hashlib
import json
import math
import re
import statistics
import unicodedata
from datetime import datetime
from benchmark import METHODOLOGY_ID, ENGINE_CORE_VERSION, CALIBRATION, WEIGHTS, STORAGE_WEIGHTS, calculate_indices

COMMUNITY = 'https://benchmark.smartdomo.de'
COMPATIBLE_VERSIONS = ('0.4.1', '0.5.0')
SYSTEM_TEXT = ('architecture', 'cpu_model', 'home_assistant', 'operating_system', 'supervisor', 'machine', 'storage_type')
SYSTEM_NUMBERS = ('logical_cpus', 'memory_total_mib', 'storage_size_gb')

def clean_text(value, limit=100):
    if (not isinstance(value, str) or len(value) > limit
            or any(unicodedata.category(c) in ('Cc', 'Cf') for c in value)):
        raise ValueError('Invalid text / Ungültiger Text')
    return value.strip()

def number(value, minimum=0, maximum=1e12):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError('Invalid measurement / Ungültiger Messwert')
    return value

def public_run(run, include_environment=False):
    if not isinstance(run, dict) or run.get('benchmark_version') not in COMPATIBLE_VERSIONS:
        raise ValueError('Requires benchmark 0.4.1 or 0.5.0 / Benchmark 0.4.1 oder 0.5.0 erforderlich')
    if run.get('methodology_id') != METHODOLOGY_ID or run.get('engine_core_version') != ENGINE_CORE_VERSION:
        raise ValueError('Incompatible methodology / Inkompatible Methodik')
    if run.get('reference', {}).get('calibration') != CALIBRATION['calibration']:
        raise ValueError('Incompatible calibration / Inkompatible Kalibrierung')
    if run.get('profile') not in ('light', 'full'):
        raise ValueError('Invalid profile / Ungültiges Profil')
    rid = run.get('result_id', '')
    if not isinstance(rid, str) or not re.fullmatch('[a-f0-9]{12,64}', rid):
        raise ValueError('Invalid result ID')
    system = run.get('system', {})
    # No device_name, entity IDs, platform string, tokens, IPs or hostnames.
    public_system = {key: clean_text(system.get(key) or 'unknown') for key in SYSTEM_TEXT}
    if public_system['storage_type'] not in ('unknown', 'sd', 'emmc', 'sata_ssd', 'nvme', 'virtual'):
        raise ValueError('Invalid storage type / Ungültige Speicherart')
    public_system.update({key: number(system.get(key) or 0) for key in SYSTEM_NUMBERS})
    tests = {}
    for key in WEIGHTS:
        source = run.get('tests', {}).get(key, {})
        if source.get('error'):
            raise ValueError('Failed test cannot be shared / Fehlerhafter Test nicht teilbar')
        fields = STORAGE_WEIGHTS if key == 'sqlite' else ('value',)
        tests[key] = {field: number(source.get(field), 1e-9) for field in fields}
    stamp = clean_text(run.get('finished_at', ''), 40)
    parsed = datetime.fromisoformat(stamp)
    if parsed.tzinfo is None:
        raise ValueError('Timestamp needs timezone')
    result = dict(result_id=rid, benchmark_version=run['benchmark_version'], methodology_id=METHODOLOGY_ID,
                  engine_core_version=ENGINE_CORE_VERSION, reference=CALIBRATION, profile=run['profile'],
                  finished_at=stamp, duration_seconds=number(run.get('duration_seconds'), .001, 86400),
                  system=public_system, tests=tests)
    if include_environment:
        env = run.get('environment', {})
        result['environment'] = {}
        for section, fields in {'temperature': ('start', 'maximum'), 'energy': ('average_w', 'peak_w', 'consumption_wh')}.items():
            values = env.get(section, {})
            result['environment'][section] = {key: number(values[key], -100 if section == 'temperature' else 0, 1e6)
                                               for key in fields if values.get(key) is not None}
    return result

def make_payload(runs, alias='', device_model='', include_environment=False):
    if not isinstance(runs, list) or len(runs) not in (1, 3):
        raise ValueError('Select one or three runs / Einen oder drei Läufe wählen')
    cleaned = [public_run(r, include_environment) for r in runs]
    if len({r['result_id'] for r in cleaned}) != len(cleaned):
        raise ValueError('Duplicate runs / Doppelte Läufe')
    first = cleaned[0]
    if any((r['profile'], r['benchmark_version'], r['system']) !=
           (first['profile'], first['benchmark_version'], first['system']) for r in cleaned):
        raise ValueError('Three runs must use the same system, version and profile / Gleiches System, Version und Profil erforderlich')
    return dict(schema=1, alias=clean_text(alias, 40), device_model=clean_text(device_model, 80), runs=cleaned)

def summarize(payload):
    runs = payload['runs']
    profile = runs[0]['profile']
    tests = {}
    for key in WEIGHTS:
        fields = STORAGE_WEIGHTS if key == 'sqlite' else ('value',)
        tests[key] = {field: statistics.median(r['tests'][key][field] for r in runs) for field in fields}
    indices, score = calculate_indices(profile, tests)
    # Overall for three runs is the median of individual overall scores.
    scores = [calculate_indices(profile, json.loads(json.dumps(r['tests'])))[1] for r in runs]
    environment = {}
    for section, fields in {'temperature': ('start', 'maximum'),
                            'energy': ('average_w', 'peak_w', 'consumption_wh')}.items():
        values = {}
        for field in fields:
            available = [r.get('environment', {}).get(section, {}).get(field) for r in runs]
            available = [value for value in available if value is not None]
            if available:
                values[field] = statistics.median(available)
        if values:
            environment[section] = values
    return dict(profile=profile, indices=indices, index=statistics.median(scores), tests=tests,
                environment=environment,
                count=len(runs), calibration=CALIBRATION['calibration'], methodology_id=METHODOLOGY_ID,
                engine_core_version=ENGINE_CORE_VERSION, benchmark_version=runs[0]['benchmark_version'])

def fingerprint(payload):
    # Same measurement cannot create another entry merely by changing its ID/date/alias.
    material = sorted(json.dumps({'profile': r['profile'], 'system': r['system'], 'tests': r['tests']}, sort_keys=True)
                      for r in payload['runs'])
    return hashlib.sha256(json.dumps(material).encode()).hexdigest()
