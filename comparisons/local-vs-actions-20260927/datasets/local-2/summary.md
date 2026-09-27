# Keyword sort latency report

**Runner validation (recorded):** 1.3.20=valid, 2.11.1=valid, 2.12.0=valid, 2.19.0=valid, 3.8.0=valid
**Reporter evidence checks / recomputation:** PASS
**Historical-boundary performance outcome:** **REPRODUCED**

Reported releases: 1.3.20, 2.11.1, 2.12.0, 2.19.0, 3.8.0.

Cell values are medians of two block medians, recomputed from the retained samples. Tables show the median across pairs, then each pair's cell value in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 6.560 (6.789, 6.330) | 6.551 (6.329, 6.772) | 1.073×, 0.935× |
| 2.11.1 | 8.096 (8.079, 8.113) | 8.152 (8.309, 7.995) | 0.972×, 1.015× |
| 2.12.0 | 21.596 (22.799, 20.392) | 6.528 (6.527, 6.530) | 3.493×, 3.123× |
| 2.19.0 | 24.828 (24.457, 25.199) | 7.048 (7.052, 7.044) | 3.468×, 3.577× |
| 3.8.0 | 15.841 (15.859, 15.823) | 6.930 (6.879, 6.980) | 2.305×, 2.267× |

## Server `took`

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 4.750 (5.000, 4.500) | 4.625 (4.250, 5.000) | 1.176×, 0.900× |
| 2.11.1 | 6.250 (6.000, 6.500) | 6.250 (6.500, 6.000) | 0.923×, 1.083× |
| 2.12.0 | 19.000 (20.000, 18.000) | 4.500 (4.500, 4.500) | 4.444×, 4.000× |
| 2.19.0 | 22.250 (22.000, 22.500) | 5.250 (5.000, 5.500) | 4.400×, 4.091× |
| 3.8.0 | 13.500 (13.500, 13.500) | 5.000 (5.000, 5.000) | 2.700×, 2.700× |

Client wall time includes HTTP/JSON decoding, excluding oracle checking. Server `took` is the returned integer-millisecond server duration, not CPU time; it excludes client/network overhead. A zero control median gives an undefined (`n/a`) ratio.

## Provenance

- Source SHA: `dddb6a785253158be0a7e0b542a1ab3b98270482`
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
