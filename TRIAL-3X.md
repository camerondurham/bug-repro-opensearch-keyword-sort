# Temporary 3.x trial — not merged into main

## Frozen question and authority

User authorized a temporary-branch GitHub Actions experiment to see 3.x measurements before deciding whether to add it to `main`. Choose **3.0.0**, the first 3.x release, to probe the major-version boundary; this says nothing about later 3.x releases. Do not rerun the four historical releases or combine separately measured runs into a new full-matrix verdict.

One manual dispatch on `trial/opensearch-3.0.0`, one hosted benchmark job capped at 15 minutes (`--max-seconds 780`, including owned-cleanup reserve), one report job capped at 5 minutes. No local Docker/OpenSearch execution, automatic retries, or automatic publication; workflow token is read-only. On invalidity, retain evidence and stop. `main` and historical `results/` stay untouched.

The runner's only change is a new supported release/Lucene identity and image digest. Same 198,000-document fixture, query, 18 shards, keyword+long sorts, first page/no pagination, 2 CPUs, 5 GiB container, 2 GiB heap, 1024→128→128→1024 fresh JVMs, 100 warmups + 100 measured requests/block × two blocks/cell. All existing response-oracle, index/segment-shape, settings-readback, deadline, lock, ownership and cleanup checks remain enabled.

## Frozen identity and primary-source checks

- [OpenSearch 3.0.0](https://github.com/opensearch-project/OpenSearch/tree/3.0.0), exact tag commit `dc4efa821904cc2d7ea7ef61c0f577d3fc0d8be9`.
- [Release dependency declaration](https://github.com/opensearch-project/OpenSearch/blob/dc4efa821904cc2d7ea7ef61c0f577d3fc0d8be9/gradle/libs.versions.toml#L3): Lucene **10.1.0**.
- [Startup setting/default and Lucene forwarding](https://github.com/opensearch-project/OpenSearch/blob/dc4efa821904cc2d7ea7ef61c0f577d3fc0d8be9/server/src/main/java/org/opensearch/search/SearchService.java#L332): `indices.query.bool.max_clause_count`, default 1024, forwarded to `IndexSearcher.setMaxClauseCount`; runtime readback is still required.
- Official Docker Hub tag `opensearchproject/opensearch:3.0.0` multi-platform index: `sha256:00565f63fa1aa1643d5a2cf61cb5f09b4aeddee2f12703f01c534f051bff1a99`.
- Frozen linux/amd64 manifest: `sha256:22c18a39aae9868d76df4ffc4713d164c81b2c5ee8be7ad67da96e0ecd5212e0`.
- Image config ID: `sha256:f7e91a0b5f857ef8ed5b76ac290bb46d159000880c67a55dc4d5e0eb07ecc6ad`.
- Manifest index and selected manifest fetched via the Docker Registry v2 API; SHA-256 recomputed from exact response bytes and matched registry headers and index references. No image/container launched during preparation.

## Interpretation and evidence

Report both paired client wall and server `took` medians and ratios, regardless of effect direction or size. No 3.x reproduction threshold is pre-assigned; single-version outcome remains `NOT_ASSESSED`. Compare descriptively with retained [2.x measurements](results/summary.md), explicitly noting different run/VM/JDK/Lucene/segment layouts across releases. Within-3.0.0 clause-ceiling pairs are the controlled comparison; a speedup or null does not prove a specific Lucene commit caused the change.

The measured source SHA and run URL are retained in the raw result. Reports/artifacts go to `trial-results/3.0.0/`, never historical `results/`. The generated summary's `main/results` provenance link refers to the historical matrix, not this trial; use the trial links below.

## Completed measurement

[Actions run 36333617456](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36333617456) **succeeded**; measured source `3ad7ec783acd769c828d79b7aeb51b7be855b1d8`. Benchmark elapsed **299.781 s**, including pull/setup/four fresh cells/cleanup. Bundled JVM: **21.0.7**. No retry or additional benchmark launched.

| Pair (order) | Client 1024 / 128 (ms) | Client ratio | Server `took` 1024 / 128 (ms) | Server ratio |
|---|---:|---:|---:|---:|
| 1 (1024→128) | 101.592 / 41.269 | 2.462× | 96.750 / 35.500 | 2.725× |
| 2 (128→1024) | 100.408 / 40.594 | 2.473× | 95.500 / 35.000 | 2.729× |

**Finding:** the setting-sensitive slowdown persists in **3.0.0** on this fixture. Lowering the ceiling reduces client latency by approximately **59.4–59.6%** in both orders; server time corroborates. This is descriptive paired evidence, not a new full-matrix verdict or a conclusion about every 3.x release.

### Historical comparison—not a contemporaneous version experiment

| Version/run | Client 1024 median (ms) | Client 128 median (ms) | Paired speedups |
|---|---:|---:|---|
| 2.19.0 / 36327603776 | 74.260 | 29.598 | 2.654×, 2.363× |
| 3.0.0 / 36333617456 | 101.000 | 40.931 | 2.462×, 2.473× |

Each setting's table value is the median across its two cell values. The new absolute medians are **36.0% higher at 1024** and **38.3% higher at 128** than the retained 2.19 run. Different hosted VMs, bundled software and independently built indexes confound that comparison: **do not call this a measured 3.x version regression**. The within-3.0.0 setting effect is the controlled finding.

### Evidence verification

- [Raw result](trial-results/3.0.0/raw/3.0.0.json), SHA-256 `4a6c43c4f28c2a617d73a2483d2967dcd9173441054f5819c3e2e9c41de7436e`.
- [Paired summary](trial-results/3.0.0/summary.md), [cell chart](trial-results/3.0.0/matrix.svg), [all 800 measured requests](trial-results/3.0.0/requests.svg), [standalone HTML](trial-results/3.0.0/report.html).
- Parent checked frozen source/query/parameters, four distinct container IDs in ABBA order, exact OpenSearch build/Lucene/image identity, oracle hash independently reconstructed from the fixture, stable before/after layouts and equal rebuilt segment shapes, all four recorded `cleanup=clean` markers, and the 780-second bound.
- Independently recomputed every client/server block and paired median from raw arrays. Raw benchmark JSON equals the visual artifact's raw JSON byte-for-byte. Offline CLI regeneration reproduces every visual artifact byte-for-byte; request SVG contains 800 measured points.
- These checks verify retained evidence. They do not recontact the hosted engine or independently certify its teardown or each response body; the frozen runner performed those live checks.
- Ten offline tests and existing reporter self-tests passed before launch. Historical raw/results and `main` are unchanged. Trial code/evidence remain only on `trial/opensearch-3.0.0` pending user review.
