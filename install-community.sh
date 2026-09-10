#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Bitte als root ausführen: sudo bash install-community.sh" >&2
  exit 1
fi

SOURCE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
APP_SOURCE="$SOURCE_DIR/community"
BENCH_SOURCE="$SOURCE_DIR/smartdomo_benchmark/app"
INSTALL_DIR=/opt/ha-benchmark-community
DATA_DIR=/var/lib/ha-benchmark
CONFIG_DIR=/etc/ha-benchmark
BACKUP_DIR=/var/backups/ha-benchmark
SITE_HTTP=/etc/apache2/sites-available/benchmark.smartdomo.de.conf
SITE_HTTPS=/etc/apache2/sites-available/benchmark.smartdomo.de-le-ssl.conf

for item in "$APP_SOURCE/service.py" "$APP_SOURCE/static/index.html" "$BENCH_SOURCE/sharing.py" "$BENCH_SOURCE/scoring_r3.py" "$BENCH_SOURCE/scoring_r4.py" "$BENCH_SOURCE/device_types.py"; do
  [[ -f "$item" ]] || { echo "Paket unvollständig: $item fehlt" >&2; exit 1; }
done
[[ -f /etc/letsencrypt/live/benchmark.smartdomo.de/fullchain.pem ]] || {
  echo "TLS-Zertifikat für benchmark.smartdomo.de fehlt. Vorbereitung zuerst ausführen." >&2
  exit 1
}

if [[ ! -s "$DATA_DIR/operator.json" ]]; then
  echo "Angaben für Datenschutz und Impressum (werden öffentlich angezeigt):"
  read -r -p "Verantwortlicher / Firmenname: " OPERATOR_NAME
  read -r -p "Vollständige ladungsfähige Anschrift: " OPERATOR_ADDRESS
  read -r -p "Kontakt-E-Mail: " OPERATOR_EMAIL
  [[ -n "$OPERATOR_NAME" && -n "$OPERATOR_ADDRESS" && "$OPERATOR_EMAIL" == *@* ]] || {
    echo "Name, vollständige Anschrift und gültig wirkende E-Mail sind erforderlich." >&2
    exit 1
  }
fi

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv sqlite3
a2enmod proxy proxy_http headers rewrite ssl >/dev/null

id ha-benchmark >/dev/null 2>&1 || useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin ha-benchmark
install -d -o root -g root -m 0755 "$INSTALL_DIR"
install -d -o ha-benchmark -g ha-benchmark -m 0750 "$DATA_DIR"
install -d -o root -g ha-benchmark -m 0750 "$CONFIG_DIR"
install -d -o root -g root -m 0700 "$BACKUP_DIR"

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
if [[ -d "$INSTALL_DIR/app" ]]; then
  tar -C "$INSTALL_DIR" -czf "$BACKUP_DIR/application-$STAMP.tar.gz" app
fi
install -d -o root -g root -m 0755 "$INSTALL_DIR/app/static"
install -m 0644 "$APP_SOURCE/service.py" "$BENCH_SOURCE/sharing.py" "$BENCH_SOURCE/scoring_r3.py" "$BENCH_SOURCE/scoring_r4.py" "$BENCH_SOURCE/device_types.py" "$INSTALL_DIR/app/"
for item in index.html ui.js style.css methodology.html methodology.js brand.png benchmark.svg favicon.svg; do
  install -m 0644 "$BENCH_SOURCE/$item" "$INSTALL_DIR/app/static/"
done
for item in index.html methodology.html methodology.js privacy.html privacy.js admin.html admin.js; do
  install -m 0644 "$APP_SOURCE/static/$item" "$INSTALL_DIR/app/static/"
done

if [[ ! -x "$INSTALL_DIR/venv/bin/gunicorn" ]]; then
  python3 -m venv "$INSTALL_DIR/venv"
  "$INSTALL_DIR/venv/bin/pip" install --disable-pip-version-check 'gunicorn==23.0.0'
fi

if [[ ! -s "$CONFIG_DIR/admin.key" ]]; then
  umask 027
  openssl rand -hex 32 > "$CONFIG_DIR/admin.key"
fi
chown root:ha-benchmark "$CONFIG_DIR/admin.key"
chmod 0640 "$CONFIG_DIR/admin.key"

if [[ ! -s "$DATA_DIR/operator.json" ]]; then
python3 - "$DATA_DIR/operator.json" "$OPERATOR_NAME" "$OPERATOR_ADDRESS" "$OPERATOR_EMAIL" <<'PY'
import json, os, sys
path, name, address, email = sys.argv[1:]
temporary = path + '.tmp'
with open(temporary, 'w', encoding='utf-8') as handle:
    json.dump({'name': name, 'address': address, 'email': email}, handle, ensure_ascii=False)
os.chmod(temporary, 0o640)
os.replace(temporary, path)
PY
fi
chown ha-benchmark:ha-benchmark "$DATA_DIR/operator.json"
chmod 0640 "$DATA_DIR/operator.json"

install -m 0644 /dev/stdin /etc/systemd/system/ha-benchmark-community.service <<'UNIT'
[Unit]
Description=HA Benchmark Community ranking
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ha-benchmark
Group=ha-benchmark
WorkingDirectory=/opt/ha-benchmark-community/app
Environment=BENCHMARK_DATA=/var/lib/ha-benchmark
Environment=BENCHMARK_ADMIN_FILE=/etc/ha-benchmark/admin.key
ExecStart=/opt/ha-benchmark-community/venv/bin/gunicorn --workers 1 --threads 4 --bind 127.0.0.1:5099 --access-logfile /dev/null --error-logfile - --timeout 30 service:application
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
ReadWritePaths=/var/lib/ha-benchmark
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
LockPersonality=true
RestrictRealtime=true
SystemCallArchitectures=native

[Install]
WantedBy=multi-user.target
UNIT

for site in "$SITE_HTTP" "$SITE_HTTPS"; do
  [[ -f "$site" ]] && cp -a "$site" "$site.before-community-$STAMP"
done

install -m 0644 /dev/stdin "$SITE_HTTP" <<'APACHE'
<VirtualHost *:80>
    ServerName benchmark.smartdomo.de
    RewriteEngine On
    RewriteRule ^ https://benchmark.smartdomo.de%{REQUEST_URI} [R=301,L,NE]
    ErrorLog ${APACHE_LOG_DIR}/benchmark-error.log
    CustomLog /dev/null combined
</VirtualHost>
APACHE

install -m 0644 /dev/stdin "$SITE_HTTPS" <<'APACHE'
<IfModule mod_ssl.c>
<VirtualHost *:443>
    ServerName benchmark.smartdomo.de
    SSLEngine On
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:5099/ connectiontimeout=5 timeout=30
    ProxyPassReverse / http://127.0.0.1:5099/
    RequestHeader unset X-Forwarded-For
    RequestHeader set X-Forwarded-Proto "https"
    Header always set Strict-Transport-Security "max-age=31536000"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "no-referrer"
    Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
    ErrorLog ${APACHE_LOG_DIR}/benchmark-error.log
    CustomLog /dev/null combined
    SSLCertificateFile /etc/letsencrypt/live/benchmark.smartdomo.de/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/benchmark.smartdomo.de/privkey.pem
    Include /etc/letsencrypt/options-ssl-apache.conf
</VirtualHost>
</IfModule>
APACHE

install -m 0750 /dev/stdin /usr/local/sbin/ha-benchmark-backup <<'BACKUP'
#!/usr/bin/env bash
set -Eeuo pipefail
DATABASE=/var/lib/ha-benchmark/results.sqlite3
DESTINATION=/var/backups/ha-benchmark
[[ -f "$DATABASE" ]] || exit 0
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
TEMPORARY="$DESTINATION/results-$STAMP.sqlite3.tmp"
sqlite3 "$DATABASE" ".backup '$TEMPORARY'"
chmod 0600 "$TEMPORARY"
mv "$TEMPORARY" "$DESTINATION/results-$STAMP.sqlite3"
find "$DESTINATION" -maxdepth 1 -type f -name 'results-*.sqlite3' -mtime +7 -delete
find "$DESTINATION" -maxdepth 1 -type f -name 'application-*.tar.gz' -mtime +30 -delete
BACKUP

install -m 0644 /dev/stdin /etc/systemd/system/ha-benchmark-backup.service <<'UNIT'
[Unit]
Description=Back up HA Benchmark SQLite database

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ha-benchmark-backup
UNIT

install -m 0644 /dev/stdin /etc/systemd/system/ha-benchmark-backup.timer <<'UNIT'
[Unit]
Description=Daily HA Benchmark database backup

[Timer]
OnCalendar=daily
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
UNIT

install -m 0644 /dev/stdin /etc/logrotate.d/ha-benchmark <<'ROTATE'
/var/log/apache2/benchmark-error.log {
    daily
    rotate 14
    missingok
    notifempty
    compress
    delaycompress
    create 0640 root adm
    sharedscripts
    postrotate
        systemctl reload apache2 >/dev/null 2>&1 || true
    endscript
}
ROTATE

apache2ctl configtest
systemctl daemon-reload
systemctl enable ha-benchmark-community.service >/dev/null
systemctl enable --now ha-benchmark-backup.timer
systemctl restart ha-benchmark-community.service
systemctl reload apache2

HEALTH=
for ATTEMPT in 1 2 3 4 5 6 7 8 9 10; do
  if HEALTH=$(curl --fail --silent --show-error http://127.0.0.1:5099/api/health 2>/dev/null); then
    break
  fi
  sleep 1
done
[[ -n "$HEALTH" ]] || {
  echo "Community-Dienst wurde nicht rechtzeitig erreichbar." >&2
  systemctl status ha-benchmark-community --no-pager -l >&2 || true
  exit 1
}
printf '%s\n' "$HEALTH"
echo
curl --fail --silent --show-error https://benchmark.smartdomo.de/api/health
echo
echo "Installation abgeschlossen: https://benchmark.smartdomo.de"
echo "Moderationsschlüssel bleibt unverändert in $CONFIG_DIR/admin.key."
