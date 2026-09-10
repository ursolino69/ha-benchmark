"""Public data contract, shared by the add-on and the ranking server."""
import hashlib
import json
import math
import re
import statistics
import unicodedata
from datetime import datetime
import scoring_r4
from device_types import infer_device_type, valid_device_type

COMMUNITY = 'https://benchmark.smartdomo.de'
CURRENT_CONTRACT = scoring_r4
CONTRACTS = {
    scoring_r4.METHODOLOGY_ID: scoring_r4,
}
COMPATIBLE_VERSIONS = ('0.7.0', '0.8.0', '0.8.1')
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

def contract_for_methodology(methodology_id):
    contract = CONTRACTS.get(methodology_id)
    if contract is None:
        raise ValueError('Incompatible methodology / Inkompatible Methodik')
    return contract

def public_run(run, include_environment=False, selected_device_type=None, device_model=''):
    if not isinstance(run, dict) or run.get('benchmark_version') not in COMPATIBLE_VERSIONS:
        raise ValueError('Requires a compatible benchmark version / Kompatible Benchmark-Version erforderlich')
    contract = contract_for_methodology(run.get('methodology_id'))
    if run.get('engine_core_version') != contract.ENGINE_CORE_VERSION:
        raise ValueError('Incompatible methodology / Inkompatible Methodik')
    supplied_calibration = run.get('reference', {}).get('calibration')
    # R4 candidate 0.7.0 stored raw values before the reference existed. Its
    # unchanged methodology ID and engine version make those runs scoreable now.
    pending_r4 = (contract is scoring_r4 and run.get('benchmark_version') == '0.7.0'
                  and supplied_calibration is None and run.get('calibration_status') == 'pending')
    if supplied_calibration != contract.CALIBRATION['calibration'] and not pending_r4:
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
    chosen_type = selected_device_type if valid_device_type(selected_device_type) else system.get('device_type')
    resolution = infer_device_type(public_system, chosen_type or 'auto', device_model)
    if not valid_device_type(resolution.get('device_type')):
        raise ValueError('Select a device type / Gerätetyp auswählen')
    public_system['device_type'] = resolution['device_type']
    tests = {}
    for key in contract.WEIGHTS:
        source = run.get('tests', {}).get(key, {})
        if source.get('error'):
            raise ValueError('Failed test cannot be shared / Fehlerhafter Test nicht teilbar')
        fields = contract.STORAGE_WEIGHTS if key == 'sqlite' else ('value',)
        tests[key] = {field: number(source.get(field), 1e-9) for field in fields}
    stamp = clean_text(run.get('finished_at', ''), 40)
    parsed = datetime.fromisoformat(stamp)
    if parsed.tzinfo is None:
        raise ValueError('Timestamp needs timezone')
    result = dict(result_id=rid, benchmark_version=run['benchmark_version'], methodology_id=contract.METHODOLOGY_ID,
                  engine_core_version=contract.ENGINE_CORE_VERSION, reference=contract.CALIBRATION, profile=run['profile'],
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

def make_payload(runs, alias='', device_model='', include_environment=False, device_type=None):
    if not isinstance(runs, list) or len(runs) not in (1, 3):
        raise ValueError('Select one or three runs / Einen oder drei Läufe wählen')
    cleaned_model = clean_text(device_model, 80)
    cleaned = [public_run(r, include_environment, device_type, cleaned_model) for r in runs]
    if len({r['result_id'] for r in cleaned}) != len(cleaned):
        raise ValueError('Duplicate runs / Doppelte Läufe')
    first = cleaned[0]
    if any((r['profile'], r['methodology_id'], r['engine_core_version'], r['reference']['calibration'], r['system']) !=
           (first['profile'], first['methodology_id'], first['engine_core_version'], first['reference']['calibration'], first['system'])
           for r in cleaned):
        raise ValueError('Three runs must use the same system, methodology and profile / Gleiches System, gleiche Methodik und gleiches Profil erforderlich')
    return dict(schema=2, alias=clean_text(alias, 40), device_model=cleaned_model,
                device_type=first['system']['device_type'], runs=cleaned)

def summarize(payload):
    runs = payload['runs']
    profile = runs[0]['profile']
    contract = contract_for_methodology(runs[0]['methodology_id'])
    tests = {}
    for key in contract.WEIGHTS:
        fields = contract.STORAGE_WEIGHTS if key == 'sqlite' else ('value',)
        tests[key] = {field: statistics.median(r['tests'][key][field] for r in runs) for field in fields}
    indices, score = contract.calculate_indices(profile, tests)
    # Overall for three runs is the median of individual overall scores.
    scores = [contract.calculate_indices(profile, json.loads(json.dumps(r['tests'])))[1] for r in runs]
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
    versions = sorted({r['benchmark_version'] for r in runs})
    spread = 0 if len(scores) == 1 else (max(scores) - min(scores)) / statistics.median(scores) * 100
    quality = {'runs': len(scores), 'spread_percent': round(spread, 1),
               'level': 'stable' if len(scores) == 3 and spread <= 5 else
                        'moderate' if len(scores) == 3 and spread <= 10 else
                        'variable' if len(scores) == 3 else 'single'}
    return dict(profile=profile, indices=indices, index=statistics.median(scores), tests=tests,
                environment=environment,
                count=len(runs), calibration=contract.CALIBRATION['calibration'], methodology_id=contract.METHODOLOGY_ID,
                engine_core_version=contract.ENGINE_CORE_VERSION, benchmark_version=versions[-1],
                benchmark_versions=versions, device_type=payload['device_type'],
                quality=quality,
                compatibility_id=f"{contract.METHODOLOGY_ID}:{contract.CALIBRATION['calibration']}:{profile}")

def fingerprint(payload):
    # Same measurement cannot create another entry merely by changing its ID/date/alias.
    material = sorted(json.dumps({'profile': r['profile'], 'system': r['system'], 'tests': r['tests']}, sort_keys=True)
                      for r in payload['runs'])
    return hashlib.sha256(json.dumps(material).encode()).hexdigest()
