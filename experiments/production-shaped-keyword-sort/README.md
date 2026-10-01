# Production-shaped keyword-sort

Test whether tenant selectivity, keyword ties and pagination explain why the clause-limit effect changes across workloads. [protocol.md](protocol.md) defines the anonymized cases and qualification rules.

Status: documentation only. The new runner is unimplemented; an exact remote run scope and output directory have not been approved.

## Workspace layout

```text
experiments/production-shaped-keyword-sort/
  README.md                 status, next task and handoff
  protocol.md               proposed tests and measurement rules
  runs/<machine>/<run>/     future retained evidence
```

The experiment name is `production-shaped-keyword-sort`; its implementation branch is `experiment/production-shaped-keyword-sort`. Create run directories only when needed. Use anonymous machine/run labels. Keep the published `results/`, existing `comparisons/` and fixed three-by-five comparison wrapper unchanged.

## Next implementation task

Implement the first OpenSearch 2.19 subset: existing-workload controls, tenant selectivity, keyword ties and explicit hit-count/pagination cases. Extend the existing offline tests that own fixture generation, ordering and reporting. Preserve the default benchmark behavior and give the new workload separate result labels. Add nested shape after those cases qualify; distributed and mixed-load cases follow later.

Keep one implementation writer at a time. Update this status and add the verified run command when a runner exists. Before any Docker run, agree on the remote machine, exact cases, output directory, resource limits and time cap. The baseline comparison guide is [../../comparisons/README.md](../../comparisons/README.md).

Offline checks from the repository root:

```bash
python3 -m unittest -v
python3 report.py --self-test
```

## Return evidence

After validation and an anonymity check, retain the approved output under `runs/<machine>/<run>/`. Each run must record the tested source commit, case/request parameters, seed, public engine/image identity, resource limits and actual command, together with raw samples, validation/cleanup status and the report. The source commit identifies the code measured, rather than the later commit containing results. Keep validity and speedup separate and retain qualified no-speedup outcomes.

Cases from this workload remain separate from the published whole-matrix comparison; result metadata must distinguish workloads.

## Agent handoff

The next handoff is the first OpenSearch 2.19 subset with offline coverage, a reproducible run command and evidence for the approved cases. Docker execution and result publication require separate authorization.

Keep private machine access details, credentials and production identifiers outside the repository. The shared handoff is this directory plus a Git commit ID; no session transcript or external note is needed.
