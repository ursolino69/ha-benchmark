# HA Benchmark

Home-Assistant-specific Light and Full benchmark with Green = 100 category indices, transparent R3
methodology, bilingual UI and opt-in Share & Compare at `benchmark.smartdomo.de`.

## Home Assistant installation

1. Publish this repository at a reachable Git URL.
2. In Home Assistant open **Settings → Apps → App Store → Repositories**.
3. Add the repository URL, install **HA Benchmark**, then open it from the sidebar.

For local development copy `smartdomo_benchmark` to `/addons/`. Light may be used for controlled
production measurements; Full is restricted to test devices and needs `allow_full_benchmark: true`.
Configuration, interpretation, privacy, sharing and troubleshooting are documented in the app's
`DOCS.md`. The exact scoring method is in [METHODOLOGY.md](METHODOLOGY.md).

## Community deployment

The small WSGI/SQLite service is designed for an existing Apache VPS and binds only to
`127.0.0.1:5099`. After TLS for `benchmark.smartdomo.de` exists, upload the release directory and run:

```bash
sudo bash install-community.sh
```

The installer asks for the legal operator details, preserves prior dedicated virtual-host files,
does not edit the existing `/ha-dashboard` configuration, enables a hardened systemd service,
daily seven-day SQLite backups and 14-day error-log rotation. See
[`community/OPERATIONS.md`](community/OPERATIONS.md) for operation, moderation and recovery.

## English

This repository contains the installable HA app and the optional public comparison service. Results
stay local unless the user previews the exact public payload and explicitly confirms publication.
Anonymous publishing supports an optional alias and a private deletion key. One- and three-run entries
are accepted; three-run medians carry a higher-quality badge but are not presented as verified.

License: MIT
