# NixOS WSL2 Ryzen 7 7800X3D result

**The keyword-sort effect reproduced on this NixOS/WSL2 machine in all three runs.**

Measured on 2026-09-28 using source [`2b23427`](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/commit/2b23427c439fe1ffdaece44b2629ac82fd80112c). All 15 local runs passed validation.

[Report](report.html) · [Summary](summary.md) · [Ratios](ratios.svg) · [Latency](latency.svg) · [Wrapper host record](host.json) · [Pre-run system capture](system.json)

| Item | Measured value |
|---|---|
| CPU | AMD Ryzen 7 7800X3D, 8 cores / 16 threads |
| OS / kernel | NixOS 26.11 under WSL2 / `6.18.33.2-microsoft-standard-WSL2` |
| Guest-visible RAM | 44.09 GiB (not physical installed RAM) |
| Docker | client 29.8.0 / server 29.7.2; overlay2, cgroup v2 |
| Python | 3.14.7 |
| Benchmark limits | Docker: 2 CPUs, 5 GiB; Java heap: 2 GiB |

The fixed protocol ran 3 matrices × 5 versions (15 local invocations), measuring 12,000 local requests. Wrapper runtime was 1,696.95 seconds (28m17s).

The generated [summary](summary.md#spread-across-repetitions-reference-excluded) flags a 22.7% paired-ratio spread for local 2.19.0. One local container's block medians fell from 30.155 to 22.778 ms. Four additional block-drift warnings belong to the retained GitHub reference. See [details](summary.md#block-drift). These are diagnostics, not steady-state or causal claims.

Command used for this run (the output directory did not yet exist):
```bash
python3 -u run_comparison.py --output comparisons/nixos-wsl2-ryzen-7800x3d
```
To intentionally replace this generated directory, use `--replace`:
```bash
python3 -u run_comparison.py --output comparisons/nixos-wsl2-ryzen-7800x3d --replace
```
Replacement regenerates the whole directory. Capture current system specs and restore any supplemental notes before committing a rerun.
The existing code, protocol, configuration, and installation were unchanged. `system.json` was captured before measurement; `host.json` was recorded by the wrapper. Windows background activity was not monitored. This example does not claim independent hardware causality or generalization to all WSL machines.
