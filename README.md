# OpenSearch keyword-sort latency regression

A small, synthetic reproduction of the **2.11.1 → 2.12.0 keyword-sort slowdown**, with 1.3.20 and 2.11.1 as negative controls. No production data, snapshots, benchmark framework, Python packages, or patched server binaries.

[![Reproduce keyword-sort latency](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/workflows/reproduce.yml/badge.svg)](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/workflows/reproduce.yml)

**Start here:** [latest measured report](results/summary.md) · [raw measurements](results/raw) · [run / rerun in Actions](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/workflows/reproduce.yml).
A green workflow means **valid measurements and published charts**, not necessarily reproduction. The report separately says `REPRODUCED` or `NOT_REPRODUCED`; noisy CI must not masquerade as a deterministic functional test.

## Visual comparison

These charts are generated from actual GitHub Actions request samples, not the historical lab numbers. Exact source revision, run link, image digests, JDK identities, and parameters are retained with the results.

![Baseline versus clause-128 client latency across OpenSearch releases](results/matrix.svg)

### Every measured query request

Same first-page query repeated in every cell. All requests are shown; fresh-JVM and block boundaries are marked. Warmups are excluded. These are not independent workloads or 800 independent JVM replicates.

![Every measured request latency, separated by release and fresh JVM](results/requests.svg)

## Reproduce with GitHub Actions

1. Open **Actions → Reproduce keyword-sort latency → Run workflow** on `main`.
2. Four isolated Linux jobs benchmark the pinned releases. Each is capped at 15 minutes; reporting at 5 minutes (at most 65 runner-minutes, typically much less). No schedule or push-triggered workloads.
3. The report job checks the complete matrix and publishes `results/` back to this private repo. The README graphs update automatically. No force pushes; source drift blocks publication.
4. Download **visual-report** for an offline, self-contained `report.html`, SVG charts, JSON measurements, and Markdown summary. Artifacts expire after 30 days; committed results remain in Git history.

Share this repository with authorized collaborators using **Settings → Collaborators**. A private link alone does not grant access. No public Pages site or external chart service is used.

## What changes?

| Release | Bundled Lucene | Expected effect of 1024 → 128 |
|---|---|---|
| 1.3.20 | 8.10.1 | Little/no effect (negative control) |
| 2.11.1 | 9.7.0 | Little/no effect (negative control) |
| 2.12.0 | 9.9.2 | Faster keyword sort |
| 2.19.0 | 9.12.1 | Faster keyword sort |

The only declared setting contrast **within each release** is:

```text
indices.query.bool.max_clause_count: 1024  versus  128
```

Both are explicitly applied **at node startup**, because older releases reject dynamic changes. `1024` is the release default. The query has **one term filter**, not hundreds of Boolean clauses:

```json
{
  "size": 250,
  "version": true,
  "query": {"bool": {"filter": [{"term": {"tenant_id": "tenant-a"}}]}},
  "sort": [{"item_key": "asc"}, {"market_id": "asc"}],
  "_source": {"excludes": ["source_records.*"]}
}
```

`track_total_hits` is deliberately omitted (release default). Each fresh index contains 198,000 deterministic documents with unique keyword sort values, permuted insertion order, 18 primary shards, and no replicas. Explicit refreshes target approximately two segments per shard; actual segment inventories are recorded, not assumed. No force merge, writes, routing, or `search_after` during measurement.

### Measurement protocol

- Four **fresh containers/JVMs per version**, ordered **1024 → 128 → 128 → 1024** (two opposite-order pairs).
- Each container: two blocks, each with 100 validated warmups then 100 measured requests. **800 measured requests/version; 3,200 total**.
- Cell latency: median of its two block medians. Both pair speedups are reported; aggregate bars are descriptive. Client wall time includes HTTP/JSON decoding, excludes oracle checking; server `took` is retained separately.
- Every response must match an independently generated oracle: 250 exact ordered IDs, both sort values, `_version`, and `_source`; no timeout or failed/skipped shards. Hashes must agree across releases/settings.
- Startup settings are read back. Fixture document/deletion counts, active/completed merges and segment identities must remain unchanged across timing blocks.
- Linux/amd64 images are digest-pinned; the exact image ID is reused across all four cells. Stock bundled JDKs are recorded. Docker enforces **2 CPUs / 5 GiB memory**, Java uses **2 GiB heap / 2 active processors** on every version.
- `REPRODUCED`: each affected release is ≥1.25× faster at 128 in **both** pairs, and each negative-control pair ratio lies within [0.80, 1.25]. These are prospective descriptive thresholds, not significance tests. A valid null is still published.
- Bounded execution, cooperative host lock, loopback-only HTTP, exact-ID/owner-label cleanup, fail-stop within each version. A failed/incomplete matrix cannot publish a success chart over the previous results.

## Run locally

Use a disposable **Linux x86-64** machine with Docker, Python 3.10+, at least 7 GiB RAM, roughly 15 GiB free disk, and no competing workloads. Python has no third-party dependencies. Security is disabled only inside fresh loopback-published containers; never point this at a real cluster.

```bash
sudo sysctl -w vm.max_map_count=262144
python3 repro.py --version 2.19.0 --output artifacts/2.19.0
# Each output directory must be new; failed evidence is not overwritten.
```

For the complete chart matrix (sequentially on one machine):

```bash
for version in 1.3.20 2.11.1 2.12.0 2.19.0; do
  python3 repro.py --version "$version" --output "local-run/$version" || break
done
python3 report.py --input local-run --output local-report
# Open local-report/report.html
```

To check the code without Docker/workloads: `python3 -m unittest -v test_repro.py` and `python3 report.py --self-test`.

## Why this can happen

Lucene's keyword-sort competitive iterator uses:

```java
final int maxTerms = Math.min(MAX_TERMS, IndexSearcher.getMaxClauseCount());
```

[Lucene #11903](https://github.com/apache/lucene/pull/11903), commit [`f1d763a`](https://github.com/apache/lucene/commit/f1d763a75014c8a7ab9654b3038b50f64faba348), raised `MAX_TERMS` **128 → 1024**. It allows earlier enumeration of competitive sort terms, which can cost more than it saves for this fixture. Lowering the shared Boolean ceiling delays that work on stock binaries. Sources: [Lucene 9.12.1 comparator](https://github.com/apache/lucene/blob/releases/lucene/9.12.1/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L547), [OpenSearch 2.19 setting registration](https://github.com/opensearch-project/OpenSearch/blob/2.19.0/server/src/main/java/org/opensearch/search/SearchService.java#L321), [forwarding to Lucene](https://github.com/opensearch-project/OpenSearch/blob/2.19.0/server/src/main/java/org/opensearch/search/SearchService.java#L469).

**This is not a blanket production fix.** The setting also restricts Boolean/expanded queries: lowering it can reject other queries. It does not silently truncate this query. This release/control matrix strongly implicates the sort threshold; it is not an isolated binary revert proving a single commit caused every historical slowdown.

## Scope and provenance

Extracted from `reports/lucene-11903-repro-20260927.py` at source-lab commit `b290835` (original file SHA-256 `228674cab284f2cb6cd695a4ff9f39d7bbaddc70da1d81341734c274a7c36037`). The lab began by investigating latency regressions after upgrading OpenSearch, including production write/cleanup “shark-fin” reports. It subsequently isolated a reproducible **read-only sorted-search** regression and the adjacent release boundary.

This minimal repo tests that narrowed finding only. It does **not** reproduce the original concurrent-write symptom, full inventory traversal, the residual cursor-page cost, relevance quality, or production compatibility. Cross-release comparisons include bundled JDK/plugin differences and run on different hosted VMs; within-release paired setting contrasts are stronger evidence. CI uses a smaller heap/CPU allocation than the historical 8-GiB-heap lab. Absolute milliseconds are hardware-dependent; request repeats are not independent replication, and two fresh pairs do not establish population confidence.

The workflow follows the simple pinned-release matrix/artifact pattern of the [routing bug reproduction](https://github.com/camerondurham/bug-repro-opensearch-routing), but adds raw latency evidence, visualizations, opposite-order controls, and a separate performance verdict. No source-lab history, private workload data, or credentials are copied here.
