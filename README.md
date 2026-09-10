# HA Benchmark

> How fast is your Home Assistant?

HA Benchmark is a reproducible performance test for Home Assistant systems. It measures seven
Home-Assistant-specific workloads instead of relying on generic CPU or disk benchmarks. Results can
be kept locally or, after an exact data preview and explicit consent, published anonymously to the
public [Share & Compare](https://benchmark.smartdomo.de) ranking.

**Current release:** 0.7.0  
**Methodology:** R4 calibration candidate  
**Supported architectures:** aarch64 and amd64  
**License:** [MIT](LICENSE)  
**App documentation:** [Deutsch](smartdomo_benchmark/DOCS.md#deutsch) · [English](smartdomo_benchmark/DOCS.md#english)

> [!IMPORTANT]
> R4 deliberately has no provisional index. Its workloads differ substantially from R3, so new
> Home Assistant Green reference measurements are required. Version 0.7.0 therefore displays R4 raw
> values only. Existing calibrated R3 results remain available in the public ranking and are never
> mixed with R4 data.

## What it measures

| Category | Planned weight | Workload |
| --- | ---: | --- |
| Core Events | 15% | Eight event types with changing payloads and complete burst processing |
| State Changes | 20% | Fresh old/new states distributed across hundreds of entities and active listener groups |
| Entity Processing | 5% | Include/exclude filtering and entity-ID validation with an 80/20 recurring/new-ID mix |
| Fresh JSON States | 10% | Creation and serialization of new Home Assistant State objects and attributes |
| Recorder Storage | 20% | Durable SQLite commits, sequential writes, random reads and a WAL checkpoint |
| HA API | 10% | Median response time of the running Home Assistant REST API |
| Parallel Core Load | 20% | State creation and serialization in separate worker processes to expose multicore capacity |

Temperature, power, energy and Linux Pressure Stall Information (PSI) can also be recorded. They are
diagnostic values only and do not affect the index.

The planned Smartdomo Index is normalized to **Home Assistant Green = 100** for each profile. It uses
a weighted geometric mean so that one exceptionally fast category cannot completely conceal a weak
one. The formula, workload sizes, storage sub-metrics, limitations and calibration protocol are
documented in [Methodology R4](METHODOLOGY.md). The previous calibrated method remains available as
[Methodology R3](METHODOLOGY-R3.md).

## Benchmark profiles

### Light

Designed for a controlled run on a production system. It still creates temporary load and storage
writes. Do not run it during backups, updates, recorder maintenance or periods of high automation
activity.

### Full

Designed exclusively for test systems. It creates substantially more events, state changes,
serialization work and durable storage operations. The profile remains locked until
`allow_full_benchmark` is explicitly enabled in the app configuration.

## Installation

HA Benchmark is a Home Assistant app and requires Home Assistant OS with the Supervisor/App Store. It
does not install as a regular Home Assistant integration or as a standalone Home Assistant Container.

[![Add the HA Benchmark repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fursolino69%2Fha-benchmark)

Alternatively, install it manually:

1. Open **Settings → Apps → App Store** in Home Assistant.
2. Open the menu and select **Repositories**.
3. Add `https://github.com/ursolino69/ha-benchmark`.
4. Select **HA Benchmark**, install it and enable **Show in sidebar**.
5. Review the configuration before starting the first benchmark.

For local development, copy `smartdomo_benchmark` to `/addons/`, reload the App Store and install the
local app.

## Producing comparable results

1. Use the same benchmark methodology and profile on every device.
2. Update Home Assistant OS and Home Assistant Core before testing.
3. Stop unnecessary apps and wait until backups, updates and database maintenance have finished.
4. Allow the device to return to a stable idle temperature.
5. Run the benchmark three times without changing the configuration.
6. Compare the median rather than the single best result.

Hardware, storage type, storage capacity, Home Assistant versions and diagnostic conditions remain
part of the result context. A three-run community entry receives a repeatability badge, but this does
not constitute independent hardware verification.

## Understanding the results

Each result card contains the measured value and unit. Once R4 calibration is complete, it will also
show the category index and its contribution to the Smartdomo Index. Higher index values are always
better; a value of 100 represents the corresponding Home Assistant Green reference measurement.

Every result card is interactive and explains:

- what the test measures;
- which Home Assistant workloads it affects;
- how its raw value should be interpreted;
- which limitations apply.

HA Benchmark measures defined performance capacity. It does not determine whether a device is
suitable for every installation, measure storage endurance, or reproduce all integrations,
automations and apps of a live household.

## Share & Compare

Results stay on the Home Assistant system unless the user starts the sharing process. Before anything
is transmitted, the app displays the complete public JSON payload and requires explicit consent.

Publishing supports:

- one run or the median of three compatible runs;
- an optional public alias and model name;
- a controlled device type for consistent ranking labels;
- optional temperature and energy values;
- a private deletion key without requiring an account.

The public service recalculates submitted scores and never trusts client-provided index values. Local
device names, hostnames, IP addresses, entity IDs, access tokens, Home Assistant configuration and
entity states are excluded. Details are documented in [Security and privacy](SECURITY.md).

R4 publishing will be enabled only after the new Green calibration has been completed. Calibrated R3
results can still be shared and compared at [benchmark.smartdomo.de](https://benchmark.smartdomo.de).

## Documentation

- [App guide: configuration, interpretation and troubleshooting](smartdomo_benchmark/DOCS.md)
- [Benchmark methodology R4](METHODOLOGY.md)
- [Previous benchmark methodology R3](METHODOLOGY-R3.md)
- [Security and privacy model](SECURITY.md)
- [Release history](smartdomo_benchmark/CHANGELOG.md)
- [Community service deployment](DEPLOYMENT.md)
- [Community service operations and recovery](community/OPERATIONS.md)

## Repository structure

| Path | Purpose |
| --- | --- |
| `smartdomo_benchmark/` | Installable Home Assistant app |
| `community/` | Public ranking service and frontend |
| `tests/` | Benchmark, sharing, service and frontend contract tests |
| `install-community.sh` | Installer for the dedicated community server |

## Development and validation

Run the automated test suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The repository includes tests for scoring directions and weights, R4 workload behavior, result
sharing, server-side validation, privacy boundaries and frontend contracts. Hardware results still
require validation on actual Home Assistant systems; passing unit tests alone does not establish a
reference calibration.

## Project status

Version 0.7.0 is the R4 calibration candidate. The next release requires controlled Home Assistant
Green Light and Full reference series, publication of their medians and dispersion, and assignment of
a new R4 calibration ID. Until then, raw R4 measurements are suitable for methodology testing but not
for cross-version ranking.
