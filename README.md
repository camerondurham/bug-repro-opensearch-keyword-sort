# OpenSearch keyword-sort latency regression

**Finding:** in the [five-version GitHub Actions run](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36336273811), lowering `indices.query.bool.max_clause_count` from 1024 to 128 sped up the same sorted query by 2.77-3.17x on 2.12.0, 2.34-2.52x on 2.19.0, and 2.05-2.06x on 3.8.0, across both opposite-order pairs. Negative controls 1.3.20 and 2.11.1 stayed near 1x. The query contains only one term filter.

**[OpenSearch 3.8.0](https://github.com/opensearch-project/OpenSearch/releases/tag/3.8.0)**, the latest stable release at selection (published August 5, 2026), is pinned by image digest in `repro.py`. Its client cell medians fall from 77.83 to 37.92 ms; server `took` corroborates at 72.88 to 32.88 ms. Both charts cover all five versions from the same source/run: 20 fresh JVMs, 4,000 measured requests, all runner checks passed and teardown recorded clean.

![Measured client latency: baseline 1024 versus control 128](results/matrix.svg)

Recompute the published numbers and charts without Docker (Python 3.10+, standard library only):

```bash
python3 report.py --input results/raw --output local-report
```

Open `local-report/report.html`. Also in this repo: [client and server summaries](results/summary.md), [every measured request](results/requests.svg), and the committed [raw records](results/raw).

<details>
<summary>All 4,000 measured requests, including 3.8.0</summary>

![Every measured request across all five releases](results/requests.svg)

</details>

## Mechanism

Lucene's keyword-sort comparator builds a postings-based competitive iterator gated by `Math.min(MAX_TERMS, IndexSearcher.getMaxClauseCount())` ([`PostingsBasedCompetitiveState`](https://github.com/apache/lucene/blob/releases/lucene/10.5.0/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L522), declared at [line 524](https://github.com/apache/lucene/blob/releases/lucene/10.5.0/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L524), gate computed at [line 581](https://github.com/apache/lucene/blob/releases/lucene/10.5.0/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L581)). [Lucene #11903](https://github.com/apache/lucene/pull/11903), commit [`f1d763a`](https://github.com/apache/lucene/commit/f1d763a75014c8a7ab9654b3038b50f64faba348), raised `MAX_TERMS` from 128 to 1024 in Lucene 9.9 (OpenSearch 2.12.0), so the comparator now enumerates competitive sort-term postings across a much wider ordinal range. On this fixture the extra enumeration costs more than it saves; lowering the Boolean ceiling to 128 shrinks the range and drops the enumeration back to doc-values ordinals on stock binaries. Lucene 10.5.0, bundled in 3.8.0, still carries both the constant and the gate. The newer doc-values [`SkipperBasedCompetitiveState`](https://github.com/apache/lucene/blob/releases/lucene/10.5.0/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L648) and its adaptive disabling ([line 694](https://github.com/apache/lucene/blob/releases/lucene/10.5.0/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L694)) apply to the skipper path; an indexed keyword sort takes the postings-based path.

## Scope

The fixture runs one term filter and sorts by keyword `item_key` then long `market_id`, repeating the first 250-hit page with no pagination. Production write/cleanup latency is out of scope. Cross-version rows mix bundled JDKs, plugins and hosted VMs; the within-version setting pairs carry the evidence. Two fresh pairs per version describe this run. Lowering the ceiling can reject other Boolean or expanded queries. The setting feeds a shared Lucene path, so the result does not single out one commit.

## Run one release

On a disposable Linux x86-64 host with Docker, Python 3.10+, at least 7 GiB RAM and roughly 15 GiB free disk, set `vm.max_map_count >= 262144` beforehand and avoid competing workloads:

```bash
python3 repro.py --version 3.8.0 --output artifacts/3.8.0
```

The runner prints both paired client and server `took` ratios and retains `result.json`. Each output directory must be new. A single-release run reports `NOT_ASSESSED`; only a full same-source matrix carries the reproduction verdict. To render retained evidence offline:

```bash
python3 report.py --input artifacts/3.8.0 --version 3.8.0 --output local-report
```

The reporter also accepts one JSON file, an Actions artifact tree, or `results/raw/`. Counts and labels follow the runner's recorded `--samples`, heap and fixture parameters; nondefault settings keep the labels the run recorded. Default reporting requires all five releases from the same measured source/run; do not splice a new 3.x run into old matrix evidence. For in-place regeneration, use `--input results/raw --output results`; raw inputs are preserved byte-for-byte. `--historical-matrix` replays the [archived original four-release dataset](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/38f9db311c3262ea2c532bda02ef5eacaf34b575/results) only.

## Minimal upstream reproducer

[`minimal_repro.py`](minimal_repro.py) is a single-file, standard-library script for filing the upstream issue, validated on 2026-09-27. It starts one stock container per version and per node-startup ceiling (two containers per version), applies the ceiling at node startup, and prints a four-version matrix with ordered-result hashes:

```bash
python3 minimal_repro.py   # --versions CSV, --docs N, --shards N, --heap G, --reverse
```

Prerequisites, defaults and the validated per-version result table are in the script docstring. It needs Docker with memory headroom above the heap it requests (default 8g), and it removes the containers and networks it created.

## Exact reduced workload

198,000 deterministic documents, permuted insertion order, 18 primary shards, no replicas. Explicit refreshes target approximately two segments/shard; actual inventories are checked. No force merge or writes during timing. The primary keyword is unique; the second sort key is a long.

```json
{
  "size": 250,
  "version": true,
  "query": {"bool": {"filter": [{"term": {"tenant_id": "tenant-a"}}]}},
  "sort": [{"item_key": "asc"}, {"market_id": "asc"}],
  "_source": {"excludes": ["source_records.*"]}
}
```

`track_total_hits` is omitted (release default). No routing, `search_after`, PIT, or pagination. Both clause ceilings apply at node startup: older releases reject dynamic changes, and 1024 is the release default.

| OpenSearch | Bundled Lucene | Role |
|---|---|---|
| 1.3.20 | 8.10.1 | Negative control |
| 2.11.1 | 9.7.0 | Negative control before the measured boundary |
| 2.12.0 | 9.9.2 | Affected release after the boundary |
| 2.19.0 | 9.12.1 | Affected later release |
| 3.8.0 | 10.5.0 | Latest stable 3.x; observed 2.05-2.06x setting effect |

3.8.0 identity: official release commit [`e5a3c569`](https://github.com/opensearch-project/OpenSearch/tree/e5a3c5691be87af6c12dbe3e158c59c04ee72973), [Lucene dependency](https://github.com/opensearch-project/OpenSearch/blob/e5a3c5691be87af6c12dbe3e158c59c04ee72973/gradle/libs.versions.toml#L3), [clause-ceiling setting](https://github.com/opensearch-project/OpenSearch/blob/e5a3c5691be87af6c12dbe3e158c59c04ee72973/server/src/main/java/org/opensearch/search/SearchService.java#L398). Official linux/amd64 image manifest `sha256:68a688de28fb9bb66601552650b91a52a9fd5e7eac5481dd2b225ecb66fd09b0` for 3.8.0 and the sibling release digests are pinned in `repro.py`; registry manifests were rehashed at selection.

- ABBA: four fresh JVMs/version, 1024 -> 128 -> 128 -> 1024. Each has two blocks with 100 validated warmups and 100 measured requests: 800 measured requests/version, 4,000 in the five-release matrix (3,200 in the retained historical run).
- Resources: digest-pinned linux/amd64 stock images; the same resolved image ID across a release's cells. Docker: 2 CPUs / 5 GiB memory; Java: 2 GiB heap / 2 active processors. Bundled JDK identities are retained.
- Metrics: a cell is the median of its two block medians, for both client wall latency and server `took`. Report both opposite-order pair ratios (1024/128); chart bars are medians across pairs. Client time includes HTTP/JSON decoding but excludes oracle checking. `took` is the integer-millisecond server duration reported by the node; it excludes client and network overhead. A zero denominator prints `n/a`.
- Historical-boundary rule: both 2.12/2.19 pairs must be >=1.25x and both 1.3/2.11 pairs within [0.80, 1.25] for `REPRODUCED`. This descriptive rule uses client latency; server timings corroborate separately. 3.8.0 is reported alongside the historical versions and excluded from that verdict. A null 3.8.0 result is valid evidence. Default matrix validity requires all five versions; missing or invalid 3.8.0 fails reporting. Explicit single-version reporting is `NOT_ASSESSED`.

## Validation scope

Runner, during the live experiment: every warmup and measured response must match the independent ordered ID/sort/version/source oracle, with 250 hits and no timeout or failed/skipped shards. Startup settings are read back. Document/deletion counts, merge counters and segment identities must stay fixed across blocks; per-shard segment document/deletion inventories must match across rebuilt cells within a release. Engine/image identities are checked. Deadlines, cooperative host lock, loopback-only HTTP and exact-ID/owner-label cleanup stay enforced; invalidity stops that release.

Reporter, offline: recomputes client/server block medians and paired ratios from timing arrays, checks recorded client medians against samples, sample counts against parameters, ABBA labels, recorded version metadata, status/cleanup markers and matching result hashes/parameters. Full response bodies and live readbacks are not retained, so recomputation plays back the runner's recorded evidence; runner validation is a recorded claim, and reporter recomputation is an evidence check. Provenance always points to the original measured source/run, even when a newer reporter regenerates the presentation.

## Repeatability and host variation

[Three complete local repetitions versus GitHub](comparisons/local-vs-actions-20260927/FINDINGS.md) are retained: 15 invocations, 60 JVMs, 12,000 measured requests on one Ryzen 7800X3D/WSL2 host, all using the same standalone runner.

- 3.8.0 was stable locally: all six paired speedups 2.267-2.320x, versus 2.047-2.059x on GitHub. Local absolute timings were much lower; don't transfer absolute milliseconds across hosts.
- 2.19.0 was unstable in magnitude: 2.844-6.475x. One default-setting JVM's client block medians fell 67.684 -> 21.189 ms, with server timing corroboration. The outlier is retained. Existing warmups do not prove steady-state timing; these records cannot identify the transient's cause.
- The qualitative effect persists, and extra repetitions are useful for reliability claims. Three runs on one WSL2 host do not estimate variation across the GitHub fleet. [All paired ratios](comparisons/local-vs-actions-20260927/ratios.svg), [absolute timings](comparisons/local-vs-actions-20260927/latency.svg), and the [replay command and interpretation](comparisons/local-vs-actions-20260927/FINDINGS.md).

The exact three-matrix command, lock rule and comparison behavior are in the [repeatability notes](comparisons/local-vs-actions-20260927/FINDINGS.md#running-the-same-matrices-locally).

## CI and offline checks

The manual [workflow](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/workflows/reproduce.yml) offers the default five-job `parallel` matrix and an opt-in `repeated` mode (three fresh VMs, each running all five versions in varied order, 70-minute matrix-job caps). `repeated` is offline-checked; it has yet to run live on GitHub. Mode details, caps, retained outputs and failure behavior: [repeatability notes](comparisons/local-vs-actions-20260927/FINDINGS.md#github-mode-comparison).

No schedules, push-triggered benchmarks, or automatic retries. A failed version stops its matrix; independent hosted jobs can finish, and missing or invalid evidence fails reporting. Artifacts are downloadable for 30 days; committed evidence remains in Git history. A green workflow means the evidence checks passed; the `REPRODUCED` verdict is a separate outcome in the summary.

Existing runner checks, reporter self-checks, and committed-raw replay coverage all run without Docker or network access:

```bash
python3 -m unittest -v
python3 report.py --self-test
```

## Provenance

Exact sources: [Lucene 9.12.1 comparator](https://github.com/apache/lucene/blob/releases/lucene/9.12.1/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L547), [OpenSearch 2.19 setting](https://github.com/opensearch-project/OpenSearch/blob/2.19.0/server/src/main/java/org/opensearch/search/SearchService.java#L321), [forwarding to Lucene](https://github.com/opensearch-project/OpenSearch/blob/2.19.0/server/src/main/java/org/opensearch/search/SearchService.java#L469).

Extracted from an earlier private investigation workspace; [`minimal_repro.py`](minimal_repro.py) publishes the one-file script unchanged (SHA-256 `228674cab284f2cb6cd695a4ff9f39d7bbaddc70da1d81341734c274a7c36037`). The original investigation concerned upgrade-related latency; this repo isolates its read-only sorted-search finding. It contains no production data, credentials or patched binaries. The GitHub Actions setup follows the pinned-release pattern of the [routing reproduction](https://github.com/camerondurham/bug-repro-opensearch-routing).

## License

Apache License 2.0, see [LICENSE](LICENSE).
