# Whole-matrix repeatability comparison

**Retained evidence checks: PASS.** No requests were pooled.

Repetitions: local-1, local-2, local-3. Reference: actions.
A reference is displayed separately and excluded from repetition spreads. Dataset labels do not establish independent physical hosts.

## Client summaries by matrix

| Version | Dataset | 1024 median ms | 128 median ms | Paired client speedups | Paired server `took` speedups |
|---|---|---:|---:|---|---|
| 1.3.20 | [local-1](datasets/local-1/summary.md) | 6.325 | 7.101 | 0.921×, 0.863× | 0.900×, 0.800× |
| 1.3.20 | [local-2](datasets/local-2/summary.md) | 6.524 | 6.531 | 1.009×, 0.990× | 1.062×, 1.000× |
| 1.3.20 | [local-3](datasets/local-3/summary.md) | 6.476 | 6.580 | 0.984×, 0.985× | 1.000×, 1.000× |
| 1.3.20 | [actions](datasets/actions/summary.md) | 31.197 | 30.554 | 1.080×, 0.965× | 1.078×, 0.981× |
| 2.11.1 | [local-1](datasets/local-1/summary.md) | 8.026 | 8.139 | 0.978×, 0.994× | 0.923×, 1.000× |
| 2.11.1 | [local-2](datasets/local-2/summary.md) | 8.157 | 8.107 | 0.998×, 1.015× | 1.000×, 1.083× |
| 2.11.1 | [local-3](datasets/local-3/summary.md) | 8.049 | 7.911 | 1.009×, 1.025× | 1.000×, 1.083× |
| 2.11.1 | [actions](datasets/actions/summary.md) | 46.297 | 47.051 | 1.000×, 0.968× | 0.994×, 0.960× |
| 2.12.0 | [local-1](datasets/local-1/summary.md) | 20.599 | 6.494 | 3.118×, 3.226× | 3.944×, 4.111× |
| 2.12.0 | [local-2](datasets/local-2/summary.md) | 20.139 | 6.496 | 3.050×, 3.152× | 3.944×, 3.944× |
| 2.12.0 | [local-3](datasets/local-3/summary.md) | 20.587 | 6.606 | 3.155×, 3.078× | 4.111×, 4.111× |
| 2.12.0 | [actions](datasets/actions/summary.md) | 73.552 | 24.821 | 2.772×, 3.167× | 3.067×, 3.561× |
| 2.19.0 | [local-1](datasets/local-1/summary.md) | 23.690 | 6.987 | 3.744×, 3.028× | 4.700×, 3.600× |
| 2.19.0 | [local-2](datasets/local-2/summary.md) | 22.004 | 7.084 | 3.133×, 3.079× | 3.950×, 3.667× |
| 2.19.0 | [local-3](datasets/local-3/summary.md) | 22.530 | 7.079 | 3.173×, 3.192× | 3.636×, 4.000× |
| 2.19.0 | [actions](datasets/actions/summary.md) | 96.907 | 39.873 | 2.516×, 2.343× | 2.766×, 2.566× |
| 3.8.0 | [local-1](datasets/local-1/summary.md) | 15.630 | 6.971 | 2.275×, 2.210× | 2.700×, 2.600× |
| 3.8.0 | [local-2](datasets/local-2/summary.md) | 15.994 | 7.001 | 2.282×, 2.287× | 2.700×, 2.700× |
| 3.8.0 | [local-3](datasets/local-3/summary.md) | 15.206 | 7.007 | 2.067×, 2.273× | 2.500×, 2.700× |
| 3.8.0 | [actions](datasets/actions/summary.md) | 77.826 | 37.918 | 2.047×, 2.059× | 2.220×, 2.214× |

## Spread across repetitions (reference excluded)

| Version | All paired ratios min / median / max | Ratio relative range | 1024 round-median relative range | 128 round-median relative range | Spread flag |
|---|---|---:|---:|---:|---|
| 1.3.20 | 0.863 / 0.984 / 1.009 | 14.8% | 3.1% | 8.7% | no |
| 2.11.1 | 0.978 / 1.003 / 1.025 | 4.8% | 1.6% | 2.8% | no |
| 2.12.0 | 3.050 / 3.135 / 3.226 | 5.6% | 2.2% | 1.7% | no |
| 2.19.0 | 3.028 / 3.153 / 3.744 | 22.7% | 7.5% | 1.4% | YES |
| 3.8.0 | 2.067 / 2.274 / 2.287 | 9.7% | 5.0% | 0.5% | no |

Relative range = (maximum − minimum) / median. Each setting's round value is the median of its two fresh-JVM cell summaries. Ratio spread includes both opposite-order pairs in every repetition.
Flags (>15% paired-ratio range or >20% setting round-median range) are descriptive diagnostics, **not validity gates or confidence intervals**. Keep every qualified observation, including outliers. Few repetitions do not estimate a host population.

## Block drift

The following cells differ by more than 20% between their two client block medians. This does not identify the cause or invalidate the retained response/layout checks; it warns against assuming steady-state timing.

- local-1, 2.19.0, JVM 1, ceiling 1024: 30.155 → 22.778 ms (-24.5%).
- actions, 2.12.0, JVM 1, ceiling 1024: 80.439 → 61.750 ms (-23.2%).
- actions, 2.19.0, JVM 1, ceiling 1024: 114.139 → 89.428 ms (-21.7%).
- actions, 2.19.0, JVM 4, ceiling 1024: 105.859 → 78.199 ms (-26.1%).
- actions, 3.8.0, JVM 1, ceiling 1024: 88.862 → 67.737 ms (-23.8%).

## Provenance

- local-1: source `2b23427c439fe1ffdaece44b2629ac82fd80112c`, run `local`; [raw records](datasets/local-1/raw).
- local-2: source `2b23427c439fe1ffdaece44b2629ac82fd80112c`, run `local`; [raw records](datasets/local-2/raw).
- local-3: source `2b23427c439fe1ffdaece44b2629ac82fd80112c`, run `local`; [raw records](datasets/local-3/raw).
- actions: source `3ed6bdcb3067af8f0a6dda4fd695473f07dac94f`, run `https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36336273811`; [raw records](datasets/actions/raw).

[Paired ratios](ratios.svg) · [Absolute latency](latency.svg) · [Standalone HTML](report.html)

Engine/image identities, parameters, query and oracle hashes agree across datasets. Each matrix is separately validated; source/run provenance may differ. Source equality, live responses, host isolation, warmup sufficiency and actual cleanup are not independently certified by this offline comparison. Per-dataset reports preserve the runner/reporter evidence distinction.
