# Keyword sort latency report

**Measurement validity:** VALID
**Performance outcome:** **REPRODUCED**

## Version summary

| Version | 1024 pair median (ms) | 128 pair median (ms) | Pair ratios (1024 / 128) |
|---|---:|---:|---|
| 1.3.20 | 27.749 (27.604, 27.894) | 27.303 (27.508, 27.099) | 1.003, 1.029 |
| 2.11.1 | 39.122 (39.793, 38.452) | 39.614 (38.951, 40.277) | 1.022, 0.955 |
| 2.12.0 | 104.609 (105.417, 103.802) | 38.104 (38.395, 37.812) | 2.746, 2.745 |
| 2.19.0 | 74.260 (78.825, 69.696) | 29.598 (29.699, 29.497) | 2.654, 2.363 |

## Provenance

- Source SHA: `4ad6043660e5ec4b4208735903fb83240067b8fc`
- Run: https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/actions/runs/36327603776
- [Exact benchmark source](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/4ad6043660e5ec4b4208735903fb83240067b8fc)
- [Published charts and raw data](https://github.com/camerondurham/bug-repro-opensearch-keyword-sort/tree/main/results)

[Matrix chart](matrix.svg) · [Every request](requests.svg) · [Offline HTML report](report.html)

Reproduction rule: both affected-release pairs ≥1.25×, both negative-control pairs within [0.80, 1.25]. Validity and this descriptive performance rule are separate.

## Validation findings

- All four releases, cells, identities, hashes, cleanup markers, and cross-release invariants validated.

## Caveats

- Bundled JDK versions are confounded across releases.
- This is a 2 CPU / 2 GiB heap CI measurement.
- It repeats one query on the first page; it is not full traversal or a production shark fin.
- Samples are not independent replicates; fresh JVMs and block boundaries are shown separately.
- The 128 setting is a coupled boolean ceiling, not an isolated production control.
