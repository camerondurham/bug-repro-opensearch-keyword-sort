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

The measured source SHA and run URL will be retained in the raw result. Reports/artifacts go to `trial-results/3.0.0/`, never historical `results/`. Results pending; no performance claim before successful live validation.
