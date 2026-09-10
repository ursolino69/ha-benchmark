# Deployment 0.7.0 · R4 calibration candidate

## 1. Community service on the prepared VPS

On Windows, place the release ZIP in Downloads and upload it:

```powershell
scp "$env:USERPROFILE\Downloads\smartdomo-ha-benchmark-v0.7.0.zip" root@217.154.22.176:/root/
ssh root@217.154.22.176
```

Then run on the VPS:

```bash
apt-get update && apt-get install -y unzip
mkdir -p /root/ha-benchmark-0.7.0
unzip -q -o /root/smartdomo-ha-benchmark-v0.7.0.zip -d /root/ha-benchmark-0.7.0
bash /root/ha-benchmark-0.7.0/smartdomo-ha-benchmark/install-community.sh
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
install/update **HA Benchmark 0.7.0**, and restart the app.

Before the first run, review every option on the **Configuration** tab. For a normal Green test,
select the actual storage type and size. Leave Full disabled on production systems. Temperature and
power entities are optional and never affect the index.

## 3. Acceptance test

1. Open the app and switch between Deutsch and English.
2. Open **Methodik R4** and click every R4 result card plus one temperature/energy card.
3. Run Light three times under comparable idle conditions. Verify raw values and `index: null` in JSON.
4. Confirm that an R4 selection explains that publication remains disabled until calibration.
5. On the community page, verify RAM in GB and the RAM/storage-size filters. Change a filter and
   confirm that the Filter button is highlighted until it is applied.
6. Confirm that the comparison checkboxes form the rightmost column below the comparison button.
7. Select an existing R3 result and verify that R3 publication/preview remains functional.
8. Check desktop/mobile layouts and logs; no alias, IP, raw payload or deletion key should appear.

## Important boundary

Version 0.7.0 introduces uncalibrated methodology R4. It does not assign provisional scores and does
not mix R4 with R3. The public service continues to rank calibrated R3 results until a separate R4
Green calibration is released. Community data remains user-submitted and not hardware-attested.
