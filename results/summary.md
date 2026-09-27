# Boolean-clause ceiling changes keyword-sorted query latency

**Runner validation (recorded):** 1.3.20=valid, 2.11.1=valid, 2.12.0=valid, 2.19.0=valid, 3.8.0=valid
**Reporter evidence checks / recomputation:** PASS
**Historical-boundary performance outcome:** **REPRODUCED**

Reported releases: 1.3.20, 2.11.1, 2.12.0, 2.19.0, 3.8.0.

Cell values are medians of two block medians, recomputed from the retained samples. Tables show the median across pairs, then each pair's cell value in parentheses. Ratios are 1024 / 128 in the two opposite orders.

## Client wall latency

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 31.197 (32.295, 30.099) | 30.554 (29.902, 31.206) | 1.080×, 0.965× |
| 2.11.1 | 46.297 (46.176, 46.419) | 47.051 (46.154, 47.947) | 1.000×, 0.968× |
| 2.12.0 | 73.552 (71.095, 76.009) | 24.821 (25.644, 23.997) | 2.772×, 3.167× |
| 2.19.0 | 96.907 (101.784, 92.029) | 39.873 (40.462, 39.285) | 2.516×, 2.343× |
| 3.8.0 | 77.826 (78.299, 77.352) | 37.918 (38.259, 37.577) | 2.047×, 2.059× |

## Server `took`

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 26.750 (27.500, 26.000) | 26.000 (25.500, 26.500) | 1.078×, 0.981× |
| 2.11.1 | 41.250 (41.000, 41.500) | 42.250 (41.250, 43.250) | 0.994×, 0.960× |
| 2.12.0 | 70.625 (68.250, 73.000) | 21.375 (22.250, 20.500) | 3.067×, 3.561× |
| 2.19.0 | 92.375 (97.500, 87.250) | 34.625 (35.250, 34.000) | 2.766×, 2.566× |
| 3.8.0 | 72.875 (73.250, 72.500) | 32.875 (33.000, 32.750) | 2.220×, 2.214× |

Client wall time includes HTTP/JSON decoding, excluding oracle checking. Server `took` is the returned integer-millisecond server duration, not CPU time; it excludes client/network overhead. A zero control median gives an undefined (`n/a`) ratio.

## Provenance

- Source SHA: `3ed6bdcb3067af8f0a6dda4fd695473f07dac94f`
- Run: https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36336273811
- [Exact benchmark source](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/3ed6bdcb3067af8f0a6dda4fd695473f07dac94f)
- [Published charts and raw data](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/main/results)

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
