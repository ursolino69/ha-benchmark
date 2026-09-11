# R4 calibration report

## Reference

| Field | Value |
|---|---|
| Calibration ID | `GREEN-CORE-2026-09-D` |
| Methodology | `CORE-2026.9.1-R4` |
| Reference device | Home Assistant Green, RK3566, 4 GB RAM, 32 GB eMMC |
| Software | Home Assistant Core 2026.9.1, HAOS 18.2, Supervisor 2026.09.0 |
| Samples | 5 Light and 5 Full runs |
| Aggregation | Median of every raw metric, separately for each profile |
| Exclusions | None |

The ten runs were recorded on the same updated Green while other apps were stopped. The reference
assigns an index of 100 to the median of each category. It is a controlled calibration of one device,
not a population estimate for every manufactured Green.

## Included runs

| Profile | Result IDs |
|---|---|
| Light | `e7fbc5a8c1a0`, `d530f47cd9b7`, `4a5a1ec17e46`, `eb8a1166a6ac`, `1d959982b34a` |
| Full | `52a91d6e94a9`, `779597dcb176`, `8124049e9dad`, `d366cb824eba`, `1a89579e2426` |

## Frozen Green references

| Raw metric | Light | Full | Direction |
|---|---:|---:|---|
| Core Events | 33,726 events/s | 34,552 events/s | higher is better |
| State Changes | 9,842 states/s | 8,900 states/s | higher is better |
| Entity Processing | 151,190 operations/s | 79,225 operations/s | higher is better |
| Fresh JSON States | 11,227 states/s | 9,775 states/s | higher is better |
| SQLite write | 11.53 MiB/s | 10.65 MiB/s | higher is better |
| SQLite commit p95 | 4.084 ms | 5.381 ms | lower is better |
| SQLite random-read p95 | 0.4054 ms | 0.3217 ms | lower is better |
| SQLite checkpoint | 161.22 ms | 1,648.02 ms | lower is better |
| HA API median | 18.59 ms | 18.88 ms | lower is better |
| Parallel Core Load | 22,943 states/s | 37,245 states/s | higher is better |

## Dispersion of the source series

CV is the sample standard deviation divided by the arithmetic mean. It is reported for transparency;
the actual reference uses the median.

| Raw metric | Light min–max | Light CV | Full min–max | Full CV |
|---|---:|---:|---:|---:|
| Core Events | 32,468–38,098 | 6.53% | 33,056–34,860 | 2.16% |
| State Changes | 9,271–10,073 | 4.14% | 8,727–9,073 | 1.50% |
| Entity Processing | 137,846–154,611 | 4.38% | 78,814–80,969 | 1.05% |
| Fresh JSON States | 11,158–11,258 | 0.38% | 9,708–9,797 | 0.42% |
| SQLite write | 11.24–11.75 MiB/s | 1.64% | 10.58–10.66 MiB/s | 0.37% |
| SQLite commit p95 | 4.025–4.243 ms | 2.07% | 5.333–5.436 ms | 0.77% |
| SQLite random-read p95 | 0.3608–0.4413 ms | 7.16% | 0.2788–0.3424 ms | 8.38% |
| SQLite checkpoint | 160.75–162.81 ms | 0.55% | 1,638.17–1,673.06 ms | 0.86% |
| HA API median | 18.56–18.94 ms | 1.01% | 18.66–18.97 ms | 0.72% |
| Parallel Core Load | 22,805–23,102 | 0.50% | 37,074–37,389 | 0.34% |

Recalculating every source run with the released integer-index algorithm gives overall indices of
98–101 for Light and 99–101 for Full. One Light run took 18.58 seconds in total while the other four took
11.05–11.22 seconds. It was retained because total duration is not scored and its scored raw metrics
were plausible. Random-read p95 shows the greatest relative dispersion; this is disclosed rather
than hidden and should be revisited when more controlled Green series are available.

## Comparability boundary

Only results with the same methodology ID, calibration ID and profile are comparable. App version
0.8.2 can calculate calibrated indices from raw R4 candidate
runs produced by 0.7.0 because the workload and engine identifiers are unchanged.
