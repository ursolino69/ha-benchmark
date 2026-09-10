"""Small WSGI service; run behind Apache with Gunicorn, never publicly bind it."""
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import parse_qs
from sharing import make_payload, summarize, fingerprint, COMMUNITY
from benchmark import METHODOLOGY_ID, CALIBRATION
from device_types import DEVICE_TYPES, infer_device_type, valid_device_type

DATA = Path(os.environ.get('BENCHMARK_DATA', '/var/lib/ha-benchmark'))
STATIC = Path(__file__).parent / 'static'
ADMIN_FILE = Path(os.environ.get('BENCHMARK_ADMIN_FILE', '/etc/ha-benchmark/admin.key'))
TOMBSTONES = DATA / 'deleted.ids'
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger('community')

def db():
    DATA.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATA / 'results.sqlite3', timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def initialize():
    with db() as conn:
        conn.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS entries (
          id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, created INTEGER NOT NULL,
          delete_hash TEXT NOT NULL, payload TEXT NOT NULL, summary TEXT NOT NULL, hidden INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS run_ids (rid TEXT PRIMARY KEY, entry_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, window INTEGER NOT NULL, count INTEGER NOT NULL);
        ''')
        if TOMBSTONES.exists():
            ids = {line.strip() for line in TOMBSTONES.read_text().splitlines() if line.strip()}
            conn.executemany('DELETE FROM run_ids WHERE entry_id=?', [(item,) for item in ids])
            conn.executemany('DELETE FROM entries WHERE id=?', [(item,) for item in ids])
    migrate_entries()


def migrate_entries():
    """Enrich existing JSON records without invalidating their measurements."""
    with db() as conn:
        rows = conn.execute('SELECT id,payload,summary FROM entries').fetchall()
        for row in rows:
            payload, summary = json.loads(row['payload']), json.loads(row['summary'])
            runs = payload.get('runs') or []
            if not runs:
                continue
            existing = payload.get('device_type') or summary.get('device_type')
            resolution = infer_device_type(runs[0].get('system', {}), existing or 'auto', payload.get('device_model', ''))
            device_type = resolution.get('device_type') if valid_device_type(resolution.get('device_type')) else 'other'
            changed = payload.get('schema') != 2 or existing != device_type or 'quality' not in summary
            payload['schema'] = 2
            payload['device_type'] = device_type
            for run in runs:
                run.setdefault('system', {})['device_type'] = device_type
            summary.update(summarize(payload))
            if changed:
                conn.execute('UPDATE entries SET payload=?,summary=? WHERE id=?',
                             (json.dumps(payload), json.dumps(summary), row['id']))

def key():
    return ADMIN_FILE.read_text().strip()

def rate_limit(ip):
    now = int(time.time())
    # Persistent, keyed hash. Raw client addresses are never stored here.
    digest = hmac.new(key().encode(), ip.encode(), hashlib.sha256).hexdigest()
    with db() as conn:
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('DELETE FROM limits WHERE window < ?', (now - 3600,))
        row = conn.execute('SELECT count FROM limits WHERE key=?', (digest,)).fetchone()
        if row and row['count'] >= 20:
            raise OverflowError('Upload limit: 20 attempts/hour / Upload-Limit: 20 Versuche/Stunde')
        conn.execute('INSERT INTO limits VALUES(?,?,1) ON CONFLICT(key) DO UPDATE SET count=count+1', (digest, now))

def public_entry(row, detail=False):
    payload, summary = json.loads(row['payload']), json.loads(row['summary'])
    result = dict(id=row['id'], created=row['created'], alias=payload['alias'], device_model=payload['device_model'],
                  system=payload['runs'][0]['system'])
    result.update(summary)
    result['device_type'] = payload.get('device_type', summary.get('device_type', 'other'))
    if detail:
        result['runs'] = payload['runs']
    else:
        result.pop('environment', None)
    return result

def application(env, start_response):
    status = '200 OK'
    headers = [('Content-Type', 'application/json; charset=utf-8'), ('Cache-Control', 'no-store'),
               ('X-Content-Type-Options', 'nosniff'), ('Referrer-Policy', 'no-referrer'),
               ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")]
    method, path = env['REQUEST_METHOD'], env.get('PATH_INFO', '/')
    try:
        admin = path.startswith('/api/admin/')
        if admin and not hmac.compare_digest(env.get('HTTP_AUTHORIZATION', ''), 'Bearer ' + key()):
            raise PermissionError('Unauthorized / Nicht autorisiert')
        body = {}
        if method in ('POST', 'DELETE'):
            origin = env.get('HTTP_ORIGIN')
            if origin and origin != COMMUNITY:
                raise PermissionError('Invalid origin')
            if env.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
                raise ValueError('application/json required')
            size = int(env.get('CONTENT_LENGTH') or 0)
            if not 0 < size <= 65536:
                raise ValueError('Request size limit: 64 KiB')
            body = json.loads(env['wsgi.input'].read(size))
            if not isinstance(body, dict):
                raise ValueError('JSON object required')
            # Apache appends the observed client to X-Forwarded-For. The last
            # address cannot be chosen by a client that prepends a forged value.
            client = env.get('HTTP_X_FORWARDED_FOR', env.get('REMOTE_ADDR', 'unknown')).split(',')[-1].strip()
            rate_limit(client[:80])
        if method == 'GET' and path == '/api/health':
            with db() as conn:
                conn.execute('SELECT 1 FROM entries LIMIT 1').fetchone()
            result = {'ok': True, 'version': '0.6.1', 'methodology_id': METHODOLOGY_ID,
                      'calibration': CALIBRATION['calibration']}
        elif method == 'POST' and path == '/api/entries':
            if body.get('consent') is not True:
                raise ValueError('Publication consent required / Zustimmung erforderlich')
            payload = make_payload(body.get('runs'), body.get('alias', ''), body.get('device_model', ''), True,
                                   body.get('device_type'))
            summary = summarize(payload)
            eid, token = secrets.token_hex(12), secrets.token_urlsafe(32)
            try:
                with db() as conn:
                    if conn.execute('SELECT count(*) FROM entries').fetchone()[0] >= 10000:
                        raise OverflowError('Capacity limit reached / Kapazitätsgrenze erreicht')
                    conn.execute('INSERT INTO entries VALUES(?,?,?,?,?,?,0)', (eid, fingerprint(payload), int(time.time()),
                                 hashlib.sha256(token.encode()).hexdigest(), json.dumps(payload), json.dumps(summary)))
                    conn.executemany('INSERT INTO run_ids VALUES(?,?)', [(r['result_id'], eid) for r in payload['runs']])
            except sqlite3.IntegrityError:
                status, result = '409 Conflict', {'error': 'Measurement already published / Messung bereits veröffentlicht'}
            else:
                LOG.info('entry_published id=%s count=%s', eid, len(payload['runs']))
                status, result = '201 Created', {'id': eid, 'url': COMMUNITY + '/?result=' + eid, 'delete_key': token}
        elif method == 'GET' and path in ('/api/entries', '/api/admin/entries'):
            query = parse_qs(env.get('QUERY_STRING', ''))
            offset = max(0, min(10000, int(query.get('offset', ['0'])[0])))
            profile = query.get('profile', ['light'])[0]
            if profile not in ('light', 'full'):
                raise ValueError('Invalid profile')
            clauses = ['(? OR hidden=0)', 'json_extract(summary,\'$.profile\')=?',
                       'json_extract(summary,\'$.methodology_id\')=?',
                       'json_extract(summary,\'$.calibration\')=?']
            parameters = [int(admin), profile, METHODOLOGY_ID, CALIBRATION['calibration']]
            device_type = query.get('device_type', [''])[0]
            storage = query.get('storage', [''])[0]
            core = query.get('core', [''])[0][:30]
            alias = query.get('alias', [''])[0].strip().lower()[:40]
            if device_type:
                if not valid_device_type(device_type):
                    raise ValueError('Invalid device type')
                clauses.append('json_extract(summary,\'$.device_type\')=?')
                parameters.append(device_type)
            if storage:
                if storage not in ('unknown', 'sd', 'emmc', 'sata_ssd', 'nvme', 'virtual'):
                    raise ValueError('Invalid storage type')
                clauses.append('json_extract(payload,\'$.runs[0].system.storage_type\')=?')
                parameters.append(storage)
            if core:
                clauses.append('json_extract(payload,\'$.runs[0].system.home_assistant\')=?')
                parameters.append(core)
            if alias:
                clauses.append('instr(lower(json_extract(payload,\'$.alias\')),?)>0')
                parameters.append(alias)
            where = ' AND '.join(clauses)
            with db() as conn:
                total = conn.execute('SELECT count(*) FROM entries WHERE ' + where, parameters).fetchone()[0]
                rows = conn.execute('SELECT * FROM entries WHERE ' + where + ' ORDER BY CAST(json_extract(summary,\'$.index\') AS REAL) DESC,created DESC LIMIT 100 OFFSET ?', parameters + [offset]).fetchall()
            result = {'entries': [dict(public_entry(r), **({'hidden': bool(r['hidden'])} if admin else {})) for r in rows],
                      'offset': offset, 'total': total, 'device_types': DEVICE_TYPES}
        elif method == 'GET' and path.startswith('/api/entries/'):
            with db() as conn:
                row = conn.execute('SELECT * FROM entries WHERE id=? AND hidden=0', (path.split('/')[-1],)).fetchone()
            if row is None:
                raise LookupError('Not found / Nicht gefunden')
            result = public_entry(row, True)
        elif method == 'DELETE' and path.startswith('/api/entries/'):
            eid = path.split('/')[-1]
            supplied = body.get('delete_key', '')
            if not isinstance(supplied, str):
                raise ValueError('Invalid key')
            with db() as conn:
                row = conn.execute('SELECT delete_hash FROM entries WHERE id=?', (eid,)).fetchone()
                if row is None or not hmac.compare_digest(row[0], hashlib.sha256(supplied.encode()).hexdigest()):
                    raise PermissionError('Invalid deletion key / Ungültiger Löschschlüssel')
                conn.execute('DELETE FROM entries WHERE id=?', (eid,))
                conn.execute('DELETE FROM run_ids WHERE entry_id=?', (eid,))
            fd = os.open(TOMBSTONES, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, 'a') as handle:
                handle.write(eid + '\n')
            LOG.info('entry_deleted id=%s', eid)
            result = {'deleted': True}
        elif method == 'POST' and path == '/api/admin/moderate':
            if type(body.get('hidden')) is not bool or not isinstance(body.get('id'), str):
                raise ValueError('id and hidden required')
            with db() as conn:
                cursor = conn.execute('UPDATE entries SET hidden=? WHERE id=?', (int(body['hidden']), body['id']))
                if not cursor.rowcount:
                    raise LookupError('Not found')
            LOG.info('entry_moderated id=%s hidden=%s', body['id'], body['hidden'])
            result = {'ok': True}
        elif method == 'GET' and path == '/api/legal':
            result = json.loads((DATA / 'operator.json').read_text())
        elif method == 'GET' and path in ('/', '/index.html', '/ui.js', '/style.css', '/methodology.html', '/methodology.js',
                                          '/brand.png', '/benchmark.svg', '/favicon.svg', '/privacy.html', '/privacy.js',
                                          '/admin.html', '/admin.js'):
            name = 'index.html' if path == '/' else path[1:]
            types = {'.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.png':'image/png', '.svg':'image/svg+xml'}
            raw = (STATIC / name).read_bytes()
            headers[0] = ('Content-Type', types[Path(name).suffix] + ('; charset=utf-8' if not name.endswith('.png') else ''))
            start_response(status, headers + [('Content-Length', str(len(raw)))])
            return [raw]
        else:
            raise LookupError('Not found / Nicht gefunden')
    except PermissionError as exc:
        status, result = '403 Forbidden', {'error': str(exc)}
    except LookupError as exc:
        status, result = '404 Not Found', {'error': str(exc)}
    except OverflowError as exc:
        status, result = '429 Too Many Requests', {'error': str(exc)}
    except (ValueError, TypeError, AttributeError) as exc:
        status, result = '400 Bad Request', {'error': str(exc)[:180]}
    except Exception:
        LOG.error('request_failed method=%s', method)
        status, result = '503 Service Unavailable', {'error': 'Service unavailable / Dienst nicht verfügbar'}
    raw = json.dumps(result, allow_nan=False).encode()
    start_response(status, headers + [('Content-Length', str(len(raw)))])
    return [raw]

initialize()
