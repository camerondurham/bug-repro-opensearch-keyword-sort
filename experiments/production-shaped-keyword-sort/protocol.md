# Production-shaped keyword-sort protocol (proposed)

[README.md](README.md) describes the experiment and handoff.

Add a separate synthetic workload to test when lowering `indices.query.bool.max_clause_count` from 1024 to 128 helps routed, multi-tenant, paginated searches. Preserve the published benchmark and its saved results. A valid result with little change or a slowdown is useful evidence.

Status: proposed tests, not implemented or executed. Documentation does not authorize a Docker run or a production replay. Agree on the output directory, selected cases, resource limits and time budget before execution.

## Anonymization and scope

This handoff uses generic field names and synthetic test parameters. It contains no organization or service names, account IDs, regions, cluster aliases, endpoints, internal URLs, private paths, deployment dates, customer identifiers, request bodies, document contents or raw production metrics.

Generate documents and requests locally from a fixed seed. Use `tenant-a`, `tenant-b`, `item-000001` and fictional market labels. Keep exported metadata limited to public engine/image identity, workload parameters and anonymous host resources. Do not copy production payloads, opaque pagination tokens, credentials, headers or logs into this repository. Audit generated reports and profiling artifacts for identifying labels and machine paths before external sharing.

The suggested percentages, segment counts and load levels below are experiment settings. They are not an inventory of a deployed cluster. Production distributions still need independently approved, anonymized characterization before claiming a workload matches them.

## Why expand the fixture

The current fixture has one tenant, globally unique primary sort keys, a numeric secondary sort key, flat documents and approximately two segments per shard. Every document matches the filter. The secondary key has no ties to resolve. Requests repeat the first page with no routing or `search_after`, and omit `track_total_hits`.

[Lucene 9.12.1's comparator](https://github.com/apache/lucene/blob/releases/lucene/9.12.1/lucene/core/src/java/org/apache/lucene/search/comparators/TermOrdValComparator.java#L547) checks the competitive ordinal range against `min(1024, max_clause_count)`. Unrelated tenants' sort values can lie inside that range. Nested children make a parent-only sort field sparse across Lucene documents. Exact total-hit counting prevents this comparator's competitive skipping. These differences can change the setting's effect; their production contribution remains unproven.

## Suggested test types

Start with OpenSearch 2.19.0/Lucene 9.12.1. Compare 1024 and 128 within each case. Use identical data, settings and resources for those two arms. Change corpus or request factors between separately labeled cases; avoid a full Cartesian matrix initially.

| Test type | Suggested cases | Question answered |
|---|---|---|
| Repeatability and positive-control tests | A/A at 1024; then the unchanged published workload at 1024/128 | Does the host give repeatable results and recover the existing setting effect? |
| Multi-tenant selectivity tests | Matching roots are 100%, 10% and 1% of roots in the searched shards | Does unrelated tenant data reduce the setting effect? |
| Sort-mapping and tie correctness tests | Numeric versus keyword secondary key; then unique versus repeated primary keys | Does the result depend on key types or missing tie-breaking work? |
| Tenant/sort-key correlation tests | Interleaved tenant-specific keys versus partially shared key vocabularies | Does filter selectivity alone describe comparator eligibility? |
| Hit-count and pagination tests | Explicit `true`, explicit `false`, and omitted `track_total_hits`; early, middle and late `search_after` pages | Which page/counting cohorts benefit? |
| Nested-document tests | 0, 1, 4 and 8 nested children per root | Does parent-only sort-field sparsity change the effect? |
| Segment and deletion tests | Approximately 2, 8 and 32 segments/shard; separately 0%, 10% and 25% deletions | Does index lifecycle change the result? |
| Routing and fan-out tests | Single shard first; then a scaled partitioned index, with routed and unrouted requests | Does distributed shard work dilute or change the effect? |
| Mixed-load tests | Read concurrency 1, 4 and 8; separately bounded background updates | Does the effect persist under ongoing indexing and contention? |
| Profiling tests | Separate captures of confirmed 1024 and 128 cases | Is time spent initializing/updating the postings iterator, or elsewhere? |

### Specify tenant and sort distributions

Define selectivity as matching root documents divided by all root documents in the searched shards. Measure nested-document inflation separately.

Begin with a single-shard diagnostic corpus. A suggested starting point is 20,000 matching roots: 100% selectivity needs 20,000 roots, while 1% needs 2,000,000. This sweep holds matching-root count fixed and intentionally increases background population and total corpus size. Record both. If the host cannot fit it, reduce matching-root count consistently across the sweep before running; document the resulting density change.

Interleave tenant keys in the global keyword term order. Include both shared item keys and tenant-specific keys. A tenant prefix that puts each tenant in a separate contiguous sort range would create a different correlation and must be labeled as its own case. Keep insertion order deterministic and decorrelated from sorted order.

Change the secondary mapping to `keyword` in its own case. Then add repeated primary keys across markets and tenants while preserving matching-root count. Use market strings whose lexical order differs from numeric order, such as `market-10` and `market-2`. Both sort fields should be indexed and have doc values. Validate ties against an independent lexical-sort oracle.

### Exercise full pagination

Use page size 250 initially. Separate these requests:

- First-page semantics: `track_total_hits=true`, no `search_after`.
- Continuation semantics: `track_total_hits=false`, with the previous page's final sort tuple.
- Diagnostic controls: omitted hit-count setting, plus explicit true/false on otherwise identical requests.

Traverse the immutable matching dataset to completion for correctness. Measure early, middle and late pages separately, and report traversal time. Select timing positions in advance. Apply repeated-request blocks to fixed validated page positions; measure complete traversals separately with their own sample counts. Validate the full ordered result sequence, exact totals where requested, versions and source fields, with no duplicates or omissions. Derive tokens independently for each arm after validating the preceding page. Different counting modes are separate experimental cases.

Exact counting is a negative control for this comparator mechanism. A large setting effect that remains with exact counting requires another explanation.

### Add nested shape and index lifecycle separately

Use a nested family with synthetic keyword, boolean and timestamp fields plus a disabled payload object. Keep root sort keys on parents only; do not copy them onto nested children. Keep the root term query fixed while changing child count. Add a nested predicate only as a later, separately labeled query case.

Record root count, matching-root count and Lucene live/deleted document counts separately. `_stats/docs` includes hidden nested documents.

For static timing, use controlled refresh schedules or restored snapshots, then wait for merges to settle. Record segment document/deletion inventories and Lucene segment versions. Test deletion fraction independently from segment count, deleting background tenants to preserve the queried result set. An old-format snapshot versus freshly built segments is a later compatibility test. Do not force-merge the baseline.

### Scale routing and load after query-path tests

A synthetic routing example is 10 primary shards with routing partition size 2. Index each document with its tenant routing value and a deterministic ID. Compare routed and unrouted searches on the same index; then test replicas and multi-node placement separately. Verify expected logical shard groups with `_search_shards`. Record successful/failed/skipped shards and actual selected groups.

For mixed-load tests, keep queried tenants immutable and update background tenants in the same searched shards. Predeclare equal offered load and write rates for both clause-limit arms. Static tests reject unexpected index-state changes; mixed-load tests deliberately allow background changes and must record them. Validate the queried result oracle in both modes. Record queues, rejections, CPU, GC and merge activity. Apply load only to an approved disposable environment.

## Measurement and qualification

Use the same pinned stock image for both limits. Restore or rebuild the same deterministic corpus. Apply startup limits and read them back on every node. Use four fresh JVMs in 1024 -> 128 -> 128 -> 1024 order to obtain opposite-order pairs. The existing two blocks of 100 validated warmups followed by 100 measured requests are a starting protocol; they do not establish steady state.

Run A/A first. Predeclare an acceptable drift bound and retain unstable observations. If A/A or block timing drifts beyond that bound, label the performance comparison inconclusive and investigate the host/JIT/GC conditions. Do not retry selectively or remove a slow cell to improve the ratio.

For each case, retain:

- Per-request server `took` and client wall time, with client decoding and validation boundaries stated.
- Per-block medians and p95, opposite-order ratios, independent JVM identities and response-oracle hashes.
- Reset-aware query/fetch counter deltas per shard operation, cache counters, segment inventories, resource limits, seed, mappings and full request parameters.

Counter deltas isolate the experiment only on a disposable environment without unrelated traffic. Request samples within one JVM are not independent replications. Report medians of block/instance summaries explicitly; do not label them pooled request percentiles.

Require whole-cluster green, no relocation, no request timeouts, expected shard coverage, correct results and clean owned-resource cleanup. Static blocks also require stable index state. Keep validity and performance outcome separate; no-speedup and slower cases remain reportable.

Profiling tests whether the setting changes time spent in `CompetitiveIterator` initialization/update work versus other query execution, fetch or GC. Profiling and instrumented builds remain separate from unprofiled stock-binary latency measurements.

## Execution order and repository boundaries

The first approved batch should cover repeatability, the published positive control, dense/sparse tenant data, keyword ties and pagination/counting modes. Add nested shape next. Segment history, distributed fan-out and mixed load follow only after those cases qualify. Agree on the selected cases and total budget before launching; this document does not request the full suite at once.

Add offline regression tests for deterministic fixture generation, lexical tie ordering, pagination oracles and retained-case metadata in the existing test files that cover those behaviors. Unit tests should verify correctness without asserting latency.

Keep `results/`, existing machine comparisons, the published query and the fixed three-by-five comparison wrapper unchanged. Label the new workload and protocol explicitly and report it separately. Existing scripts do not implement this proposed suite. Verify that any new reporter can distinguish workload/query parameters and cannot silently pool unlike cases.

Use no-speedup cases to test the proposed explanations. Sparse filtering that reduces the setting effect supports a data-shape interaction. Benefit confined to continuation pages supports cohort dilution. Cost outside the postings iterator shifts the investigation to another mechanism. None of those outcomes by itself proves fidelity to a production workload.
