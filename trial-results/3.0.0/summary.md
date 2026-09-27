# Keyword sort latency report

**Runner validation (recorded):** 3.0.0=valid
**Reporter evidence checks / recomputation:** PASS
**Full-matrix performance outcome:** **NOT_ASSESSED**

Cell values are medians of two block medians, recomputed from the retained samples. Tables show the median across pairs, then each pair's cell value in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 3.0.0 | 101.000 (101.592, 100.408) | 40.931 (41.269, 40.594) | 2.462×, 2.473× |

## Server `took`

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 3.0.0 | 96.125 (96.750, 95.500) | 35.250 (35.500, 35.000) | 2.725×, 2.729× |

Client wall time includes HTTP/JSON decoding, excluding oracle checking. Server `took` is the returned integer-millisecond server duration, not CPU time; it excludes client/network overhead. A zero control median gives an undefined (`n/a`) ratio.

## Provenance

- Source SHA: `3ad7ec783acd769c828d79b7aeb51b7be855b1d8`
- Run: https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36333617456
- [Exact benchmark source](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/3ad7ec783acd769c828d79b7aeb51b7be855b1d8)
- [Published charts and raw data](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/main/results)

[Matrix chart](matrix.svg) · [Every request](requests.svg) · [Offline HTML report](report.html)

Reproduction rule: both affected-release pairs ≥1.25×, both negative-control pairs within [0.80, 1.25]. Validity and this descriptive performance rule are separate.

## Runner validation versus reporter recomputation

- The runner performed live response-oracle, settings, index-state, identity and owned-cleanup checks. Its `status`, hashes, identity/layout snapshots and cleanup markers are retained claims.
- The reporter checks those records' structure, declared sample counts, ABBA labels, recorded version numbers, clean markers and matching hashes/parameters across the selected releases. It recomputes client/server block medians and paired ratios from raw timing arrays, and compares client block medians with the recorded values.
- The reporter does not contact Docker/OpenSearch or revalidate live settings/ownership. Full response bodies and every live readback are not retained; it cannot independently replay the response oracle or certify that cleanup occurred. This is evidence replay, not a new experiment.

### Reporter findings

- Retained evidence checks and timing recomputation passed.
- No full-matrix verdict: all four releases are required; paired single-version results are descriptive.

Recorded parameters: `{"block_warmups": 100, "chunk": 5000, "docs": 198000, "heap": "2g", "max_seconds": 780, "samples": 100, "shards": 18}`.

## Limitations

- Bundled JDK versions and hosted VMs are confounded across releases.
- Container CPU limit is 2; heap and sample counts are recorded above (published run: 2 GiB heap).
- Reduced synthetic fixture: keyword `item_key` + long `market_id` sorts; repeated first page only, no pagination.
- Not a production write/cleanup shark-fin reproduction, full traversal, or isolated commit revert.
- Samples are not independent replicates; fresh JVMs and block boundaries are shown separately.
- The 128 setting also limits Boolean/expanded queries; it is not blanket production advice.
