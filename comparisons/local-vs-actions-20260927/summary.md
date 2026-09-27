# Whole-matrix repeatability comparison

**Retained evidence checks: PASS.** No requests were pooled.

Repetitions: local-1, local-2, local-3. Reference: actions.
A reference is displayed separately and excluded from repetition spreads. Dataset labels do not establish independent physical hosts.

## Client summaries by matrix

| Version | Dataset | 1024 median ms | 128 median ms | Paired client speedups | Paired server `took` speedups |
|---|---|---:|---:|---|---|
| 1.3.20 | [local-1](datasets/local-1/summary.md) | 6.134 | 6.496 | 0.979×, 0.912× | 1.000×, 0.800× |
| 1.3.20 | [local-2](datasets/local-2/summary.md) | 6.560 | 6.551 | 1.073×, 0.935× | 1.176×, 0.900× |
| 1.3.20 | [local-3](datasets/local-3/summary.md) | 6.280 | 6.521 | 1.019×, 0.913× | 1.125×, 0.900× |
| 1.3.20 | [actions](datasets/actions/summary.md) | 31.197 | 30.554 | 1.080×, 0.965× | 1.078×, 0.981× |
| 2.11.1 | [local-1](datasets/local-1/summary.md) | 8.055 | 8.113 | 0.992×, 0.993× | 0.923×, 0.923× |
| 2.11.1 | [local-2](datasets/local-2/summary.md) | 8.096 | 8.152 | 0.972×, 1.015× | 0.923×, 1.083× |
| 2.11.1 | [local-3](datasets/local-3/summary.md) | 8.148 | 8.120 | 1.007×, 1.000× | 1.000×, 1.000× |
| 2.11.1 | [actions](datasets/actions/summary.md) | 46.297 | 47.051 | 1.000×, 0.968× | 0.994×, 0.960× |
| 2.12.0 | [local-1](datasets/local-1/summary.md) | 20.956 | 6.456 | 3.271×, 3.221× | 4.167×, 4.111× |
| 2.12.0 | [local-2](datasets/local-2/summary.md) | 21.596 | 6.528 | 3.493×, 3.123× | 4.444×, 4.000× |
| 2.12.0 | [local-3](datasets/local-3/summary.md) | 19.743 | 6.567 | 3.012×, 3.001× | 3.889×, 3.889× |
| 2.12.0 | [actions](datasets/actions/summary.md) | 73.552 | 24.821 | 2.772×, 3.167× | 3.067×, 3.561× |
| 2.19.0 | [local-1](datasets/local-1/summary.md) | 32.424 | 7.020 | 6.475×, 2.844× | 9.389×, 3.273× |
| 2.19.0 | [local-2](datasets/local-2/summary.md) | 24.828 | 7.048 | 3.468×, 3.577× | 4.400×, 4.091× |
| 2.19.0 | [local-3](datasets/local-3/summary.md) | 24.175 | 6.956 | 3.316×, 3.636× | 4.150×, 4.450× |
| 2.19.0 | [actions](datasets/actions/summary.md) | 96.907 | 39.873 | 2.516×, 2.343× | 2.766×, 2.566× |
| 3.8.0 | [local-1](datasets/local-1/summary.md) | 15.981 | 6.927 | 2.295×, 2.320× | 2.700×, 3.000× |
| 3.8.0 | [local-2](datasets/local-2/summary.md) | 15.841 | 6.930 | 2.305×, 2.267× | 2.700×, 2.700× |
| 3.8.0 | [local-3](datasets/local-3/summary.md) | 16.022 | 7.007 | 2.275×, 2.298× | 2.700×, 2.455× |
| 3.8.0 | [actions](datasets/actions/summary.md) | 77.826 | 37.918 | 2.047×, 2.059× | 2.220×, 2.214× |

## Spread across repetitions (reference excluded)

| Version | All paired ratios min / median / max | Ratio relative range | 1024 round-median relative range | 128 round-median relative range | Spread flag |
|---|---|---:|---:|---:|---|
| 1.3.20 | 0.912 / 0.957 / 1.073 | 16.8% | 6.8% | 0.8% | YES |
| 2.11.1 | 0.972 / 0.996 / 1.015 | 4.3% | 1.1% | 0.5% | no |
| 2.12.0 | 3.001 / 3.172 / 3.493 | 15.5% | 8.8% | 1.7% | YES |
| 2.19.0 | 2.844 / 3.523 / 6.475 | 103.1% | 33.2% | 1.3% | YES |
| 3.8.0 | 2.267 / 2.296 / 2.320 | 2.3% | 1.1% | 1.2% | no |

Relative range = (maximum − minimum) / median. Each setting's round value is the median of its two fresh-JVM cell summaries. Ratio spread includes both opposite-order pairs in every repetition.
Flags (>15% paired-ratio range or >20% setting round-median range) are descriptive diagnostics, **not validity gates or confidence intervals**. Keep every qualified observation, including outliers. Few repetitions do not estimate a host population.

## Block drift

The following cells differ by more than 20% between their two client block medians. This does not identify the cause or invalidate the retained response/layout checks; it warns against assuming steady-state timing.

- local-1, 2.19.0, JVM 1, ceiling 1024: 67.684 → 21.189 ms (-68.7%).
- actions, 2.12.0, JVM 1, ceiling 1024: 80.439 → 61.750 ms (-23.2%).
- actions, 2.19.0, JVM 1, ceiling 1024: 114.139 → 89.428 ms (-21.7%).
- actions, 2.19.0, JVM 4, ceiling 1024: 105.859 → 78.199 ms (-26.1%).
- actions, 3.8.0, JVM 1, ceiling 1024: 88.862 → 67.737 ms (-23.8%).

## Provenance

- local-1: source `dddb6a785253158be0a7e0b542a1ab3b98270482`, run `local`; [raw records](datasets/local-1/raw).
- local-2: source `dddb6a785253158be0a7e0b542a1ab3b98270482`, run `local`; [raw records](datasets/local-2/raw).
- local-3: source `dddb6a785253158be0a7e0b542a1ab3b98270482`, run `local`; [raw records](datasets/local-3/raw).
- actions: source `3ed6bdcb3067af8f0a6dda4fd695473f07dac94f`, run `https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36336273811`; [raw records](datasets/actions/raw).

[Paired ratios](ratios.svg) · [Absolute latency](latency.svg) · [Standalone HTML](report.html)

Engine/image identities, parameters, query and oracle hashes agree across datasets. Each matrix is separately validated; source/run provenance may differ. Source equality, live responses, host isolation, warmup sufficiency and actual cleanup are not independently certified by this offline comparison. Per-dataset reports preserve the runner/reporter evidence distinction.
