# Keyword sort latency report

**Runner validation (recorded):** 1.3.20=valid, 2.11.1=valid, 2.12.0=valid, 2.19.0=valid
**Reporter evidence checks / recomputation:** PASS
**Full-matrix performance outcome:** **REPRODUCED**

Cell values are medians of two block medians, recomputed from the retained samples. Tables show the median across pairs, then each pair's cell value in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 27.749 (27.604, 27.894) | 27.303 (27.508, 27.099) | 1.003×, 1.029× |
| 2.11.1 | 39.122 (39.793, 38.452) | 39.614 (38.951, 40.277) | 1.022×, 0.955× |
| 2.12.0 | 104.609 (105.417, 103.802) | 38.104 (38.395, 37.812) | 2.746×, 2.745× |
| 2.19.0 | 74.260 (78.825, 69.696) | 29.598 (29.699, 29.497) | 2.654×, 2.363× |

## Server `took`

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 22.750 (22.500, 23.000) | 22.250 (22.500, 22.000) | 1.000×, 1.045× |
| 2.11.1 | 34.750 (35.500, 34.000) | 35.500 (35.000, 36.000) | 1.014×, 0.944× |
| 2.12.0 | 99.625 (100.000, 99.250) | 32.500 (32.500, 32.500) | 3.077×, 3.054× |
| 2.19.0 | 69.875 (74.500, 65.250) | 24.750 (25.000, 24.500) | 2.980×, 2.663× |

Client wall time includes HTTP/JSON decoding, excluding oracle checking. Server `took` is the returned integer-millisecond server duration, not CPU time; it excludes client/network overhead. A zero control median gives an undefined (`n/a`) ratio.

## Provenance

- Source SHA: `4ad6043660e5ec4b4208735903fb83240067b8fc`
- Run: https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36327603776
- [Exact benchmark source](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/4ad6043660e5ec4b4208735903fb83240067b8fc)
- [Published charts and raw data](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/main/results)

[Matrix chart](matrix.svg) · [Every request](requests.svg) · [Offline HTML report](report.html)

Reproduction rule: both affected-release pairs ≥1.25×, both negative-control pairs within [0.80, 1.25]. Validity and this descriptive performance rule are separate.

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
