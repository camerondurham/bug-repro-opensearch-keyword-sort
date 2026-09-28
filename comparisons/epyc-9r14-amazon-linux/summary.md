# Whole-matrix repeatability comparison

**Retained evidence checks: PASS.** No requests were pooled.

Repetitions: local-1, local-2, local-3. Reference: actions.
A reference is displayed separately and excluded from repetition spreads. Dataset labels do not establish independent physical hosts.

## Client summaries by matrix

| Version | Dataset | 1024 median ms | 128 median ms | Paired client speedups | Paired server `took` speedups |
|---|---|---:|---:|---|---|
| 1.3.20 | [local-1](datasets/local-1/summary.md) | 12.277 | 12.801 | 0.937×, 0.982× | 0.947×, 1.000× |
| 1.3.20 | [local-2](datasets/local-2/summary.md) | 12.180 | 12.331 | 1.082×, 0.900× | 1.111×, 0.900× |
| 1.3.20 | [local-3](datasets/local-3/summary.md) | 11.643 | 12.103 | 0.968×, 0.957× | 0.941×, 1.000× |
| 1.3.20 | [actions](datasets/actions/summary.md) | 31.197 | 30.554 | 1.080×, 0.965× | 1.078×, 0.981× |
| 2.11.1 | [local-1](datasets/local-1/summary.md) | 14.469 | 14.777 | 1.007×, 0.952× | 1.000×, 0.958× |
| 2.11.1 | [local-2](datasets/local-2/summary.md) | 14.643 | 14.247 | 1.015×, 1.041× | 1.043×, 1.000× |
| 2.11.1 | [local-3](datasets/local-3/summary.md) | 15.037 | 14.648 | 1.050×, 1.004× | 1.043×, 1.000× |
| 2.11.1 | [actions](datasets/actions/summary.md) | 46.297 | 47.051 | 1.000×, 0.968× | 0.994×, 0.960× |
| 2.12.0 | [local-1](datasets/local-1/summary.md) | 76.719 | 12.383 | 6.423×, 5.971× | 7.947×, 7.421× |
| 2.12.0 | [local-2](datasets/local-2/summary.md) | 72.622 | 11.317 | 6.497×, 6.340× | 8.118×, 8.118× |
| 2.12.0 | [local-3](datasets/local-3/summary.md) | 72.593 | 10.933 | 6.554×, 6.726× | 8.059×, 8.688× |
| 2.12.0 | [actions](datasets/actions/summary.md) | 73.552 | 24.821 | 2.772×, 3.167× | 3.067×, 3.561× |
| 2.19.0 | [local-1](datasets/local-1/summary.md) | 76.125 | 12.528 | 6.009×, 6.140× | 7.316×, 7.262× |
| 2.19.0 | [local-2](datasets/local-2/summary.md) | 72.822 | 11.990 | 6.309×, 5.843× | 7.944×, 7.079× |
| 2.19.0 | [local-3](datasets/local-3/summary.md) | 73.575 | 12.246 | 6.027×, 5.989× | 7.368×, 7.368× |
| 2.19.0 | [actions](datasets/actions/summary.md) | 96.907 | 39.873 | 2.516×, 2.343× | 2.766×, 2.566× |
| 3.8.0 | [local-1](datasets/local-1/summary.md) | 38.513 | 11.972 | 4.414×, 1.996× | 5.556×, 2.222× |
| 3.8.0 | [local-2](datasets/local-2/summary.md) | 44.461 | 12.391 | 3.617×, 3.560× | 4.342×, 4.184× |
| 3.8.0 | [local-3](datasets/local-3/summary.md) | 46.538 | 12.179 | 3.820×, 3.822× | 4.806×, 4.500× |
| 3.8.0 | [actions](datasets/actions/summary.md) | 77.826 | 37.918 | 2.047×, 2.059× | 2.220×, 2.214× |

## Spread across repetitions (reference excluded)

| Version | All paired ratios min / median / max | Ratio relative range | 1024 round-median relative range | 128 round-median relative range | Spread flag |
|---|---|---:|---:|---:|---|
| 1.3.20 | 0.900 / 0.962 / 1.082 | 18.9% | 5.2% | 5.7% | YES |
| 2.11.1 | 0.952 / 1.011 / 1.050 | 9.7% | 3.9% | 3.6% | no |
| 2.12.0 | 5.971 / 6.460 / 6.726 | 11.7% | 5.7% | 12.8% | no |
| 2.19.0 | 5.843 / 6.018 / 6.309 | 7.7% | 4.5% | 4.4% | no |
| 3.8.0 | 1.996 / 3.719 / 4.414 | 65.0% | 18.0% | 3.4% | YES |

Relative range = (maximum − minimum) / median. Each setting's round value is the median of its two fresh-JVM cell summaries. Ratio spread includes both opposite-order pairs in every repetition.
Flags (>15% paired-ratio range or >20% setting round-median range) are descriptive diagnostics, **not validity gates or confidence intervals**. Keep every qualified observation, including outliers. Few repetitions do not estimate a host population.

## Block drift

The following cells differ by more than 20% between their two client block medians. This does not identify the cause or invalidate the retained response/layout checks; it warns against assuming steady-state timing.

- local-1, 3.8.0, JVM 1, ceiling 1024: 75.422 → 31.328 ms (-58.5%).
- local-2, 3.8.0, JVM 1, ceiling 1024: 61.162 → 28.052 ms (-54.1%).
- local-2, 3.8.0, JVM 4, ceiling 1024: 64.108 → 24.521 ms (-61.8%).
- local-3, 3.8.0, JVM 1, ceiling 1024: 68.899 → 24.149 ms (-65.0%).
- local-3, 3.8.0, JVM 4, ceiling 1024: 68.129 → 24.974 ms (-63.3%).
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
