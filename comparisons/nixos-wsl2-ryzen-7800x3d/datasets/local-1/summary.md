# Boolean-clause ceiling changes keyword-sorted query latency

**Runner validation (recorded):** 1.3.20=valid, 2.11.1=valid, 2.12.0=valid, 2.19.0=valid, 3.8.0=valid
**Reporter evidence checks / recomputation:** PASS
**Historical-boundary performance outcome:** **REPRODUCED**

Reported releases: 1.3.20, 2.11.1, 2.12.0, 2.19.0, 3.8.0.

Each block value is a median of its retained samples. A container result is the median of its two block medians. Tables show the median of the two container results for each setting, followed by both results in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | Default limit 1024 (ms) | Lowered limit 128 (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 6.325 (6.337, 6.314) | 7.101 (6.884, 7.318) | 0.921×, 0.863× |
| 2.11.1 | 8.026 (7.892, 8.160) | 8.139 (8.072, 8.206) | 0.978×, 0.994× |
| 2.12.0 | 20.599 (20.289, 20.909) | 6.494 (6.506, 6.482) | 3.118×, 3.226× |
| 2.19.0 | 23.690 (26.467, 20.913) | 6.987 (7.069, 6.905) | 3.744×, 3.028× |
| 3.8.0 | 15.630 (15.840, 15.419) | 6.971 (6.964, 6.978) | 2.275×, 2.210× |

## Server `took`

| Version | Default limit 1024 (ms) | Lowered limit 128 (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 4.250 (4.500, 4.000) | 5.000 (5.000, 5.000) | 0.900×, 0.800× |
| 2.11.1 | 6.250 (6.000, 6.500) | 6.500 (6.500, 6.500) | 0.923×, 1.000× |
| 2.12.0 | 18.125 (17.750, 18.500) | 4.500 (4.500, 4.500) | 3.944×, 4.111× |
| 2.19.0 | 20.750 (23.500, 18.000) | 5.000 (5.000, 5.000) | 4.700×, 3.600× |
| 3.8.0 | 13.250 (13.500, 13.000) | 5.000 (5.000, 5.000) | 2.700×, 2.600× |

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
