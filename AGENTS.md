# Local benchmark results

When collecting, replacing, or contributing local benchmark results, read
[`comparisons/README.md`](comparisons/README.md).

1. Get explicit user authorization before launching a Docker benchmark; docs or
   tooling work alone is not permission to benchmark.
2. Agree on the machine-specific output directory and the expensive three-by-five
   scope. Check the guide's prerequisites and use a quiet host.
3. Run the wrapper into that output directory. The runner handles its shared
   lock; do not add an outer lock.
4. Use `--replace` only when authorized to replace that exact machine directory.
5. Verify success, the `host.json` source provenance, the `comparison.json`
   `valid` field, and the report even when the result shows no speedup.
6. Stage only the authorized output directory. Keep unrelated files and the
   `results/` baseline untouched; inspect the staged diff before committing or
   opening a PR, and commit/push only when authorized.

For the proposed production-shaped workload, start with the [experiment handoff](experiments/production-shaped-keyword-sort/README.md). Its experimental case set is separate from the fixed three-by-five comparison workflow above. Agree on its exact cases and output directory before execution; the authorization, provenance, validation and result-retention rules still apply.

For code-only changes, run `python3 -m unittest -v` and
`python3 report.py --self-test` offline. Do not alter the experiment to obtain
a desired ratio. Keep benchmark details in the comparison guide rather than
copying commands into this file.
