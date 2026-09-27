# OpenSearch keyword-sort latency regression

**Finding:** in the [retained GitHub Actions run](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36327603776), lowering `indices.query.bool.max_clause_count` from **1024 to 128** sped up the same sorted query by **2.75× on 2.12.0** and **2.36–2.65× on 2.19.0**, across both opposite-order pairs. Negative controls **1.3.20 and 2.11.1 stayed near 1×**. The query contains only one term filter.

The regular matrix now includes **[OpenSearch 3.8.0](https://github.com/opensearch-project/OpenSearch/releases/tag/3.8.0)**, the latest stable release at selection (published August 5, 2026). It is pinned exactly, not to a moving `latest` tag. **3.8.0 has not yet been measured here**; the charts below retain the original four-version run until a fresh matrix run is authorized and completes.

![Measured client latency: baseline 1024 versus control 128](results/matrix.svg)

**Recompute the published numbers and charts without Docker** (Python 3.10+, standard library only):

```bash
python3 report.py --input results/raw --historical-matrix --output local-report
```

Open `local-report/report.html`. [Client and server summaries](results/summary.md) · [every measured request](results/requests.svg) · [committed raw records](results/raw).

**Limitations:** this reduced synthetic fixture sorts by **keyword `item_key` + long `market_id`**, repeating the first 250-hit page with **no pagination**. It is not a full traversal or reproduction of production write/cleanup “shark-fin” latency. Cross-release comparisons include different bundled JDKs/plugins and hosted VMs; within-release setting contrasts are stronger evidence. Two fresh pairs are descriptive, not population confidence. Lowering the clause ceiling can reject other Boolean/expanded queries—**not blanket production advice**. This is not an isolated binary revert proving a single causal commit.

## Run one release

On a disposable Linux x86-64 host with Docker, Python 3.10+, at least 7 GiB RAM and roughly 15 GiB free disk, set `vm.max_map_count >= 262144` beforehand and avoid competing workloads:

```bash
python3 repro.py --version 3.8.0 --output artifacts/3.8.0
```

The runner prints **both paired client and server `took` ratios** and retains `result.json`. Each output directory must be new. A single-release run does **not** issue a full-matrix reproduction verdict. To render its retained evidence offline:

```bash
python3 report.py --input artifacts/3.8.0 --version 3.8.0 --output local-report
```

The reporter also accepts one JSON file, an Actions artifact tree, or `results/raw/`. Counts and labels follow the runner's recorded `--samples`, heap and fixture parameters; nondefault settings are not relabeled as the published experiment. Default reporting requires all five releases from the same measured source/run; do not splice a new 3.x run into old matrix evidence. `--historical-matrix` explicitly replays the original four-release dataset (omit it for a new five-release dataset). For in-place historical regeneration, use `--input results/raw --historical-matrix --output results`; raw inputs are preserved byte-for-byte.

## Exact reduced workload

198,000 deterministic documents, permuted insertion order, 18 primary shards, no replicas. Explicit refreshes target approximately two segments/shard; actual inventories are checked. No force merge or writes during timing. The primary keyword is unique; the second sort is a **long**, not another keyword.

```json
{
  "size": 250,
  "version": true,
  "query": {"bool": {"filter": [{"term": {"tenant_id": "tenant-a"}}]}},
  "sort": [{"item_key": "asc"}, {"market_id": "asc"}],
  "_source": {"excludes": ["source_records.*"]}
}
```

`track_total_hits` is omitted (release default). No routing, `search_after`, PIT, or pagination. Both clause ceilings are explicitly applied **at node startup**: older releases reject dynamic changes; 1024 is the release default.

| OpenSearch | Bundled Lucene | Role |
|---|---|---|
| 1.3.20 | 8.10.1 | Negative control |
| 2.11.1 | 9.7.0 | Negative control before the measured boundary |
| 2.12.0 | 9.9.2 | Affected release after the boundary |
| 2.19.0 | 9.12.1 | Affected later release |
| 3.8.0 | 10.5.0 | Latest stable 3.x; effect not presumed |

3.8.0 identity: official release commit [`e5a3c569`](https://github.com/opensearch-project/OpenSearch/tree/e5a3c5691be87af6c12dbe3e158c59c04ee72973), [Lucene dependency](https://github.com/opensearch-project/OpenSearch/blob/e5a3c5691be87af6c12dbe3e158c59c04ee72973/gradle/libs.versions.toml#L3), [clause-ceiling setting](https://github.com/opensearch-project/OpenSearch/blob/e5a3c5691be87af6c12dbe3e158c59c04ee72973/server/src/main/java/org/opensearch/search/SearchService.java#L398). Official linux/amd64 image manifest `sha256:68a688de28fb9bb66601552650b91a52a9fd5e7eac5481dd2b225ecb66fd09b0` is fixed in `repro.py`; registry manifest bytes were independently rehashed at selection.

- **ABBA:** four fresh JVMs/version, **1024 → 128 → 128 → 1024**. Each has two blocks, each with 100 validated warmups and 100 measured requests: **800 measured requests/version, 4,000 in the five-release matrix** (3,200 in the retained historical run).
- **Resources:** digest-pinned linux/amd64 stock images; same resolved image ID across a release's cells. Docker: 2 CPUs / 5 GiB memory; Java: 2 GiB heap / 2 active processors. Bundled JDK identities are retained.
- **Metrics:** a cell is the median of its two block medians, for both client wall latency and server `took`. Report both opposite-order pair ratios (1024/128); chart bars are medians across pairs. Client time includes HTTP/JSON decoding but excludes oracle checking. `took` is integer-millisecond server duration, **not CPU time**, and excludes client/network overhead. A zero denominator is reported as `n/a`, not infinity.
- **Historical-boundary rule:** both 2.12/2.19 pairs must be ≥1.25× and both 1.3/2.11 pairs within [0.80, 1.25] for `REPRODUCED`. This descriptive rule uses client latency; server timings corroborate separately. **3.8.0 is reported alongside them, not presumed affected and not included in that historical verdict.** A null 3.8.0 result is valid evidence. Default matrix validity requires all five versions; missing/invalid 3.8.0 fails reporting. Explicit single-version reporting is `NOT_ASSESSED`.

## What is checked—and by whom?

**Runner, during the live experiment:** every warmup/measured response must match the independent ordered ID/sort/version/source oracle, with 250 hits and no timeout or failed/skipped shards. Startup settings are read back. Document/deletion counts, merge counters and segment identities must stay fixed across blocks; per-shard segment document/deletion inventories must match across rebuilt cells within a release. Engine/image identities are checked. Deadlines, cooperative host lock, loopback-only HTTP and exact-ID/owner-label cleanup remain enforced; invalidity stops that release.

**Reporter, offline:** recomputes client/server block medians and paired ratios from timing arrays, checks recorded client medians against samples, sample counts against parameters, ABBA labels, recorded version metadata, status/cleanup markers and matching result hashes/parameters. It cannot independently replay the response oracle or certify actual settings, index state or cleanup: full response bodies and every live readback are **not retained**. Runner validation is a recorded claim; reporter recomputation is an evidence check, **not a new experiment**. Provenance always points to the original measured source/run, even when a newer reporter regenerates the presentation.

## GitHub Actions and offline checks

[Workflow](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/workflows/reproduce.yml): manual dispatch only, five isolated version jobs capped at 15 minutes each, then a 5-minute report job. No schedule, push-triggered benchmarks, or automatic retries. Complete reports publish to `results/`; raw artifacts and the self-contained HTML report are downloadable for 30 days, while committed evidence remains in Git history. A green workflow means accepted evidence and publication, **not necessarily `REPRODUCED`**. Private-repo collaborators need explicit access.

Existing runner checks, reporter self-checks, and committed-raw replay coverage all run without Docker or network access:

```bash
python3 -m unittest -v
python3 report.py --self-test
```

## Original Lucene 9.x source lead and provenance

Lucene's keyword-sort competitive iterator uses `Math.min(MAX_TERMS, IndexSearcher.getMaxClauseCount())`. [Lucene #11903](https://github.com/apache/lucene/pull/11903), commit [`f1d763a`](https://github.com/apache/lucene/commit/f1d763a75014c8a7ab9654b3038b50f64faba348), raised `MAX_TERMS` **128 → 1024**, allowing earlier enumeration of competitive sort terms. That extra work can cost more than it saves on this fixture; lowering the shared Boolean ceiling delays it on stock binaries.

Exact sources: [Lucene 9.12.1 comparator](https://github.com/apache/lucene/blob/releases/lucene/9.12.1/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L547), [OpenSearch 2.19 setting](https://github.com/opensearch-project/OpenSearch/blob/2.19.0/server/src/main/java/org/opensearch/search/SearchService.java#L321), [forwarding to Lucene](https://github.com/opensearch-project/OpenSearch/blob/2.19.0/server/src/main/java/org/opensearch/search/SearchService.java#L469).

Extracted from source-lab `reports/lucene-11903-repro-20260927.py` at `b290835` (SHA-256 `228674cab284f2cb6cd695a4ff9f39d7bbaddc70da1d81341734c274a7c36037`). The original investigation concerned upgrade-related latency; this repo isolates its read-only sorted-search finding, not the whole production symptom. No production data, snapshots, patched binaries, credentials, source-lab history, or external Python packages are included. Actions follows the simple pinned-release pattern of the [routing reproduction](https://github.com/camerondurham/bug-repro-opensearch-routing).
