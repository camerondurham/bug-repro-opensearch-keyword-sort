# Boolean-clause ceiling changes keyword-sorted query latency

**Runner validation (recorded):** 1.3.20=valid, 2.11.1=valid, 2.12.0=valid, 2.19.0=valid, 3.8.0=valid
**Reporter evidence checks / recomputation:** PASS
**Historical-boundary performance outcome:** **REPRODUCED**

Reported releases: 1.3.20, 2.11.1, 2.12.0, 2.19.0, 3.8.0.

Each block value is a median of its retained samples. A container result is the median of its two block medians. Tables show the median of the two container results for each setting, followed by both results in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | Default limit 1024 (ms) | Lowered limit 128 (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 12.277 (12.172, 12.382) | 12.801 (12.992, 12.609) | 0.937×, 0.982× |
| 2.11.1 | 14.469 (14.601, 14.337) | 14.777 (14.496, 15.058) | 1.007×, 0.952× |
| 2.12.0 | 76.719 (78.976, 74.462) | 12.383 (12.296, 12.471) | 6.423×, 5.971× |
| 2.19.0 | 76.125 (72.821, 79.429) | 12.528 (12.120, 12.937) | 6.009×, 6.140× |
| 3.8.0 | 38.513 (53.375, 23.652) | 11.972 (12.093, 11.851) | 4.414×, 1.996× |

## Server `took`

| Version | Default limit 1024 (ms) | Lowered limit 128 (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 9.250 (9.000, 9.500) | 9.500 (9.500, 9.500) | 0.947×, 1.000× |
| 2.11.1 | 11.500 (11.500, 11.500) | 11.750 (11.500, 12.000) | 1.000×, 0.958× |
| 2.12.0 | 73.000 (75.500, 70.500) | 9.500 (9.500, 9.500) | 7.947×, 7.421× |
| 2.19.0 | 72.875 (69.500, 76.250) | 10.000 (9.500, 10.500) | 7.316×, 7.262× |
| 3.8.0 | 35.000 (50.000, 20.000) | 9.000 (9.000, 9.000) | 5.556×, 2.222× |

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
