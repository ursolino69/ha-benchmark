# Deployment 0.6.1

## 1. Community service on the prepared VPS

On Windows, place the release ZIP in the current PowerShell directory and upload it:

```powershell
scp .\smartdomo-ha-benchmark-v0.6.1.zip root@217.154.22.176:/root/
ssh root@217.154.22.176
```

Then run on the VPS:

```bash
apt-get update && apt-get install -y unzip
mkdir -p /root/ha-benchmark-0.6.1
unzip -q -o /root/smartdomo-ha-benchmark-v0.6.1.zip -d /root/ha-benchmark-0.6.1
bash /root/ha-benchmark-0.6.1/smartdomo-ha-benchmark/install-community.sh
```

On the first installation the installer asks for operator/company name, complete service address and
contact email. Updates preserve these values and the private moderation key.

Validate afterwards:

```bash
curl -fsS https://benchmark.smartdomo.de/api/health
systemctl status ha-benchmark-community --no-pager
systemctl list-timers ha-benchmark-backup.timer
```

Open these pages:

- `https://benchmark.smartdomo.de`
- `https://benchmark.smartdomo.de/methodology.html`
- `https://benchmark.smartdomo.de/privacy.html`
- `https://benchmark.smartdomo.de/admin.html` (moderation key required)

The installer only replaces the two dedicated `benchmark.smartdomo.de` virtual-host files. It does
not edit `000-default.conf`, port 5001, or the existing `/ha-dashboard` mapping.

## 2. Home Assistant app

Publish the repository contents through the existing custom app repository, or copy the complete
`smartdomo_benchmark` directory into the HAOS local apps/add-ons directory. Refresh the App Store,
install/update **HA Benchmark 0.6.1**, and restart the app.

Before the first run, review every option on the **Configuration** tab. For a normal Green test,
select the actual storage type and size. Leave Full disabled on production systems. Temperature and
power entities are optional and never affect the index.

## 3. Acceptance test

1. Open the app and switch between Deutsch and English.
2. Open **Methodik R3** and click one result card plus one temperature/energy card.
3. Run Light three times under comparable idle conditions.
4. Select all three history entries and open **Share & Compare**.
5. Verify the controlled device type, optionally enter a model and alias, inspect the complete JSON preview, consent and publish.
6. Confirm the entry has the 3-run median badge and compare it with another entry.
7. Download the private deletion key, then test deletion with a disposable publication.
8. Publish another disposable entry, hide/show it on `/admin.html`, and confirm it disappears/reappears.
9. Check logs; no alias, IP address, raw payload or deletion key should appear.

## Important boundary

Version 0.6.1 keeps methodology R3 and calibration C unchanged from 0.4.1/0.5.0. The ranking groups
compatible runs by methodology, calibration and profile. Community data is user-submitted and
plausibility-checked, not hardware-attested.
