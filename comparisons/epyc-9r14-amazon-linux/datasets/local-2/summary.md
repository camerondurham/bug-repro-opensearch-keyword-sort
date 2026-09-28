# Boolean-clause ceiling changes keyword-sorted query latency

**Runner validation (recorded):** 1.3.20=valid, 2.11.1=valid, 2.12.0=valid, 2.19.0=valid, 3.8.0=valid
**Reporter evidence checks / recomputation:** PASS
**Historical-boundary performance outcome:** **REPRODUCED**

Reported releases: 1.3.20, 2.11.1, 2.12.0, 2.19.0, 3.8.0.

Each block value is a median of its retained samples. A container result is the median of its two block medians. Tables show the median of the two container results for each setting, followed by both results in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | Default limit 1024 (ms) | Lowered limit 128 (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 12.180 (12.856, 11.505) | 12.331 (11.884, 12.778) | 1.082×, 0.900× |
| 2.11.1 | 14.643 (14.671, 14.614) | 14.247 (14.448, 14.045) | 1.015×, 1.041× |
| 2.12.0 | 72.622 (72.365, 72.879) | 11.317 (11.138, 11.495) | 6.497×, 6.340× |
| 2.19.0 | 72.822 (74.853, 70.791) | 11.990 (11.865, 12.116) | 6.309×, 5.843× |
| 3.8.0 | 44.461 (44.607, 44.314) | 12.391 (12.333, 12.449) | 3.617×, 3.560× |

## Server `took`

| Version | Default limit 1024 (ms) | Lowered limit 128 (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 9.500 (10.000, 9.000) | 9.500 (9.000, 10.000) | 1.111×, 0.900× |
| 2.11.1 | 11.750 (12.000, 11.500) | 11.500 (11.500, 11.500) | 1.043×, 1.000× |
| 2.12.0 | 69.000 (69.000, 69.000) | 8.500 (8.500, 8.500) | 8.118×, 8.118× |
| 2.19.0 | 69.375 (71.500, 67.250) | 9.250 (9.000, 9.500) | 7.944×, 7.079× |
| 3.8.0 | 40.500 (41.250, 39.750) | 9.500 (9.500, 9.500) | 4.342×, 4.184× |

Client wall time includes HTTP/JSON decoding, excluding oracle checking. Server `took` is the returned integer-millisecond server duration, not CPU time; it excludes client/network overhead. A zero control median gives an undefined (`n/a`) ratio.

## Provenance

- Source SHA: `2b23427c439fe1ffdaece44b2629ac82fd80112c`
- Run: local

[Matrix chart](matrix.svg) · [Every request](requests.svg) · [Offline HTML report](report.html)

Historical-boundary rule: both 2.12.0/2.19.0 pairs ≥1.25×, both 1.3.20/2.11.1 pairs within [0.80, 1.25]. 3.8.0 is measured descriptively, not assumed affected or used to decide that historical verdict. Default matrix validity requires all five releases; explicit historical replay requires the original four.

## Runner validation versus reporter recomputation

- The runner performed live response-oracle, settings, index-state, identity and owned-cleanup checks. Its `status`, hashes, identity/layout snapshots and cleanup markers are retained claims.
- The reporter checks those records' structure, declared sample counts, ABBA labels, recorded version numbers, clean markers and matching hashes/parameters across the selected releases. It recomputes client/server block medians and paired ratios from raw timing arrays, and compares client block medians with the recorded values.
- The reporter does not contact Docker/OpenSearch or revalidate live settings/ownership. Full response bodies and every live readback are not retained; it cannot independently replay the response oracle or certify that cleanup occurred. This is evidence replay, not a new experiment.

### Reporter findings

- Retained evidence checks and timing recomputation passed.

Recorded parameters: `{"block_warmups": 100, "chunk": 5000, "docs": 198000, "heap": "2g", "max_seconds": 780, "samples": 100, "shards": 18}`.

## Limitations

- Bundled JDK versions and hosted VMs are confounded across releases.
- Container CPU limit is 2; heap and sample counts are recorded above (published run: 2 GiB heap).
- Reduced synthetic fixture: keyword `item_key` + long `market_id` sorts; repeated first page only, no pagination.
- Not a production write/cleanup shark-fin reproduction, full traversal, or isolated commit revert.
- Samples are not independent replicates; fresh JVMs and block boundaries are shown separately.
- The 128 setting also limits Boolean/expanded queries; it is not blanket production advice.
