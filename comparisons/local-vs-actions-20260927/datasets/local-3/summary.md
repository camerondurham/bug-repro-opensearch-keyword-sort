# Keyword sort latency report

**Runner validation (recorded):** 1.3.20=valid, 2.11.1=valid, 2.12.0=valid, 2.19.0=valid, 3.8.0=valid
**Reporter evidence checks / recomputation:** PASS
**Historical-boundary performance outcome:** **REPRODUCED**

Reported releases: 1.3.20, 2.11.1, 2.12.0, 2.19.0, 3.8.0.

Cell values are medians of two block medians, recomputed from the retained samples. Tables show the median across pairs, then each pair's cell value in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 6.280 (6.270, 6.291) | 6.521 (6.151, 6.891) | 1.019×, 0.913× |
| 2.11.1 | 8.148 (8.251, 8.046) | 8.120 (8.191, 8.048) | 1.007×, 1.000× |
| 2.12.0 | 19.743 (19.822, 19.664) | 6.567 (6.582, 6.552) | 3.012×, 3.001× |
| 2.19.0 | 24.175 (23.164, 25.185) | 6.956 (6.985, 6.926) | 3.316×, 3.636× |
| 3.8.0 | 16.022 (15.860, 16.184) | 7.007 (6.971, 7.044) | 2.275×, 2.298× |

## Server `took`

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 4.500 (4.500, 4.500) | 4.500 (4.000, 5.000) | 1.125×, 0.900× |
| 2.11.1 | 6.250 (6.500, 6.000) | 6.250 (6.500, 6.000) | 1.000×, 1.000× |
| 2.12.0 | 17.500 (17.500, 17.500) | 4.500 (4.500, 4.500) | 3.889×, 3.889× |
| 2.19.0 | 21.500 (20.750, 22.250) | 5.000 (5.000, 5.000) | 4.150×, 4.450× |
| 3.8.0 | 13.500 (13.500, 13.500) | 5.250 (5.000, 5.500) | 2.700×, 2.455× |

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
