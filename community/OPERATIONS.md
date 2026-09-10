# Community server operations

## Status and logs

```bash
systemctl status ha-benchmark-community --no-pager
journalctl -u ha-benchmark-community -n 100 --no-pager
curl -fsS https://benchmark.smartdomo.de/api/health
```

The service logs publication IDs and moderation actions, but no aliases, deletion keys,
request paths or client IP addresses. Apache access logging is disabled for this virtual host.

## Moderation

Open `https://benchmark.smartdomo.de/admin.html` and paste the admin key shown during
installation. Read it again with:

```bash
cat /etc/ha-benchmark/admin.key
```

The browser keeps it only in the current tab (`sessionStorage`). Hiding an entry is reversible.

## Backups

SQLite is backed up daily and snapshots older than seven days are removed:

```bash
systemctl list-timers ha-benchmark-backup.timer
/usr/local/sbin/ha-benchmark-backup
ls -lh /var/backups/ha-benchmark
```

`/var/lib/ha-benchmark/deleted.ids` is deliberately separate from the database snapshots.
Keep that file when restoring a database: application startup reapplies deletions so an old
backup cannot resurrect user-deleted entries.

## Update and rollback

Run the installer from the new release directory. It backs up the prior application and both
dedicated Apache virtual-host files before replacing them. The existing `/ha-dashboard`
configuration in `000-default.conf`, the database, deletion tombstones, operator details and
moderation key are not changed.

Release 0.6 migrates existing public entries in place: it adds a controlled device type,
methodology compatibility identifier and three-run stability metadata without changing raw
measurements or public IDs. Verify the migration with:

```bash
curl -fsS https://benchmark.smartdomo.de/api/health
journalctl -u ha-benchmark-community -n 50 --no-pager
sqlite3 /var/lib/ha-benchmark/results.sqlite3 'PRAGMA integrity_check;'
```

To inspect the preserved virtual hosts:

```bash
ls -1 /etc/apache2/sites-available/benchmark.smartdomo.de*.before-community-*
ls -1 /var/backups/ha-benchmark/application-*.tar.gz
```

After manually restoring selected files, run:

```bash
apache2ctl configtest
systemctl restart ha-benchmark-community
systemctl reload apache2
```
