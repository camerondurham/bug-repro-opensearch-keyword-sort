#!/usr/bin/env python3
"""Standalone version-matrix repro for the OpenSearch keyword-sort regression
(Lucene #11903).

Single file, standard library only. For EACH selected OpenSearch version it starts one
stock Docker container, bulk-indexes the same high-cardinality keyword fixture, measures
a keyword-sorted query under alternating clause ceilings (ABAB blocks, each a fresh
dynamic settings PUT with readback), and prints a per-version matrix:

    indices.query.bool.max_clause_count: 1024 (default)  <->  128

The query itself has ONE boolean clause; the setting's second (undocumented-for-sorts)
role is Lucene's keyword-sort competitive-pruning cutoff,
min(MAX_TERMS, IndexSearcher.getMaxClauseCount()) — TermOrdValComparator.java line 547
(Lucene 9.12.1), raised 128 -> 1024 by lucene commit f1d763a (lucene#11903, shipped in
OpenSearch 2.12.0). Expected matrix: 1.3.20 (Lucene 8.10.1, no competitive-iterator path)
and 2.11.1 (Lucene 9.7, MAX_TERMS still 128) show NO setting effect — negative controls;
2.12.0 and 2.19.0 (MAX_TERMS=1024) show the regression at 1024 and the restoration at 128.

Validated with these defaults on 2026-09-27 (198000 docs / 18 shards, ~2
segments/shard, 8g heap, single node; two containers per version with the ceiling
applied at node startup — pre-2.13 releases reject the dynamic PUT; two same-setting
blocks of 100 samples each per container, merge/doc counters stable, explicit
deterministic _ids):

    version    default(1024)   node-128    speedup   results
    1.3.20         7.079 ms      7.139 ms     0.99x   identical
    2.11.1         8.485 ms      8.516 ms     1.00x   identical
    2.12.0        18.228 ms      7.103 ms     2.57x   identical
    2.19.0        19.103 ms      7.714 ms     2.48x   identical

The introduction boundary is inside the matrix: the regression appears exactly where
#11903 landed (2.11.1 -> 2.12.0), both negative controls are flat, and a node-applied
128 restores both affected versions with identical results.

Usage:
    python3 lucene-11903-repro-20260927.py [--versions CSV] [--docs N] [--shards N]
                                           [--heap G] [--reverse]
The script owns its (uniquely named) containers/networks exactly and always tears them
down; cleanup failures are reported as UNKNOWN, never as clean. A version whose
measurement fails is reported and the matrix continues; exit is nonzero if any version
failed.
Note: --docs must be coprime with 104729 (any value not divisible by that prime works).
Prerequisites: a running Docker daemon with memory headroom above the --heap value
(8g heap needs >= ~10g Docker memory); image tags resolve to the released bits;
throughput and runtime are machine-specific.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request

PAGE_SIZE = 250
MULTIPLIER = 104729  # coprime with docs (prime): sorted rank decorrelated from insertion order
SUFFIX = f"{os.getpid()}-{int(time.time())}"
RUN = f"osprune-repro-{SUFFIX}"
INDEX = "prune-repro"
ENGINES = {
    "1.3.20": "opensearchproject/opensearch:1.3.20",   # Lucene 8.10.1: no pruning machinery
    "2.11.1": "opensearchproject/opensearch:2.11.1",   # Lucene 9.7: MAX_TERMS still 128
    "2.12.0": "opensearchproject/opensearch:2.12.0",   # Lucene 9.9.2: #11903 landed here
    "2.19.0": "opensearchproject/opensearch:2.19.0",   # Lucene 9.12.1
}


def sh(*args):
    return subprocess.run(list(args), capture_output=True, text=True)


def docker(*args):
    result = sh("docker", *args)
    if result.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)} failed: {result.stderr.strip()[:400]}")
    return result.stdout


def container_logs_tail(container):
    result = sh("docker", "logs", "--tail", "40", container)
    return (result.stdout + result.stderr).strip()[-2000:]


def http(port, method, path, body=None, timeout=120):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError(f"HTTP {exc.code} for {method} {path}: {detail}") from exc


def effective_setting(port):
    settings = http(port, "GET",
                    "/_cluster/settings?flat_settings=true&include_defaults=true")
    for layer in ("persistent", "transient", "defaults"):
        value = (settings.get(layer) or {}).get("indices.query.bool.max_clause_count")
        if value is not None:
            return int(value)
    raise RuntimeError("max_clause_count readback missing")


def wait_ready(port, index, deadline_s=300, container=None):
    """``index=None`` waits for base reachability; an index name additionally requires
    that index green with zero unassigned shards (the fixture is 0-replica)."""
    started = time.monotonic()
    while time.monotonic() - started < deadline_s:
        try:
            base = http(port, "GET", "/_cluster/health", timeout=5)
            if base.get("status") not in ("green", "yellow"):
                time.sleep(2)
                continue
            if index is None:
                return
            index_health = http(
                port, "GET",
                f"/_cluster/health/{index}?wait_for_status=green&timeout=5s", timeout=5)
            if index_health.get("status") == "green" and \
                    index_health.get("unassigned_shards", 1) == 0:
                return
        except Exception:
            pass
        time.sleep(2)
    tail = container_logs_tail(container) if container else ""
    raise RuntimeError(f"cluster/index did not become green in time; logs:\n{tail}")


def validate_hits(response, shards, hasher):
    if response.get("timed_out") is not False:
        raise RuntimeError(f"search timed_out: {response.get('timed_out')!r}")
    shard_info = response.get("_shards") or {}
    if shard_info.get("total") != shards or shard_info.get("successful") != shards \
            or shard_info.get("failed", 0) != 0 or shard_info.get("skipped", 0) != 0:
        raise RuntimeError(f"shard accounting invalid: {shard_info!r}")
    hits = (response.get("hits") or {}).get("hits") or []
    if len(hits) != PAGE_SIZE:
        raise RuntimeError(f"expected {PAGE_SIZE} hits, got {len(hits)}")
    for hit in hits:
        hasher.update(json.dumps(
            [hit.get("_id"), hit.get("sort"), hit.get("_version"), hit.get("_source")],
            separators=(",", ":")).encode())


def index_layout(port):
    # request group is singular; the response nests the counters under 'merges'
    stats = http(port, "GET", f"/{INDEX}/_stats/docs,merge")
    primaries = stats["indices"][INDEX]["primaries"]
    return primaries["merges"]["total"], primaries["docs"]["count"]


def engine_version(port):
    return http(port, "GET", "/")["version"]["number"]


def index_fixture(port, args):
    http(port, "PUT", f"/{INDEX}", {
        "settings": {"number_of_shards": args.shards, "number_of_replicas": 0,
                     "refresh_interval": "-1"},
        "mappings": {"properties": {
            "item_key": {"type": "keyword"},
            "market_id": {"type": "long"},
            "tenant_id": {"type": "keyword"}}}})
    wait_ready(port, INDEX, container=None)
    started = time.monotonic()
    total_chunks = math.ceil(args.docs / args.chunk)
    refresh_every = max(1, total_chunks // args.segments_per_shard)
    for index, start in enumerate(range(0, args.docs, args.chunk), start=1):
        lines = []
        for ordinal in range(start, min(start + args.chunk, args.docs)):
            rank = (ordinal * MULTIPLIER) % args.docs
            # explicit deterministic _id so ordered results are identical across containers
            lines.append(json.dumps({"index": {"_index": INDEX,
                                               "_id": f"item-{rank:09d}"}}))
            lines.append(json.dumps({
                "item_key": f"item-{rank:09d}",
                "market_id": rank % 16,
                "tenant_id": "tenant-a"}))
        payload = ("\n".join(lines) + "\n").encode()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/_bulk", data=payload, method="POST")
        req.add_header("Content-Type", "application/x-ndjson")
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read().decode())
            if result.get("errors"):
                first_bad = next(item for item in result["items"]
                                 if item["index"].get("error"))
                raise RuntimeError(f"bulk error at chunk {start}: {first_bad}")
        if index % refresh_every == 0:
            http(port, "POST", "/_refresh", timeout=600)
    http(port, "PUT", f"/{INDEX}/_settings", {"refresh_interval": "1s"})
    http(port, "POST", "/_refresh", timeout=600)
    count = http(port, "GET", f"/{INDEX}/_count")["count"]
    if count != args.docs:
        raise RuntimeError(f"indexed {count} != {args.docs}")
    return time.monotonic() - started


def run_container(version, tag, node_ceiling, args, suffix):
    """One owned container at one startup-applied clause ceiling: index the fixture,
    run two same-setting blocks (stability repeat), return block medians + hash."""
    network = f"{RUN}-{version}-{suffix}-net"
    container = f"{RUN}-{version}-{suffix}-os"
    port = None
    try:
        docker("network", "create", network)
        docker("run", "-d", "--name", container, "--network", network,
               "-p", "127.0.0.1::9200",  # loopback-only, dynamically allocated host port
               "-e", f"OPENSEARCH_JAVA_OPTS=-Xms{args.heap} -Xmx{args.heap}",
               "-e", "discovery.type=single-node",
               "-e", "DISABLE_SECURITY_PLUGIN=true",
               "-e", "DISABLE_INSTALL_DEMO_CONFIG=true",
               # pre-2.13 releases do not allow dynamic updates of this setting, so the
               # ceiling is applied at node startup via an env-provided node setting
               "-e", f"indices.query.bool.max_clause_count={node_ceiling}",
               ENGINES[version])
        port_line = docker("port", container, "9200/tcp").strip().splitlines()[0]
        port = int(port_line.rsplit(":", 1)[1])
        wait_ready(port, None, container=container)
        observed = engine_version(port)
        indexed_s = index_fixture(port, args)
        wait_ready(port, INDEX, container=container)
        sys.stderr.write(f"[repro] {version}/{suffix}: indexed {args.docs} docs in "
                         f"{indexed_s:.1f}s (observed engine {observed}, node ceiling "
                         f"{node_ceiling})\n")

        query = {
            "size": PAGE_SIZE,
            "version": True,
            "query": {"bool": {"filter": [{"term": {"tenant_id": "tenant-a"}}]}},
            "sort": [{"item_key": "asc"}, {"market_id": "asc"}],
            "_source": {"excludes": ["source_records.*"]},
        }
        if observed.split(".")[0] != "1":
            observed_ceiling = effective_setting(port)
            if observed_ceiling != node_ceiling:
                raise RuntimeError(f"node ceiling readback {observed_ceiling} != "
                                   f"{node_ceiling} (defaults reflection)")
        walls_all = []
        block_medians = []
        hashes = set()
        for block_index in range(2):
            for _ in range(args.block_warmups):
                http(port, "POST", f"/{INDEX}/_search", query)
            merge_before, docs_before = index_layout(port)
            walls = []
            for _ in range(args.samples):
                t0 = time.perf_counter()
                response = http(port, "POST", f"/{INDEX}/_search", query)
                walls.append((time.perf_counter() - t0) * 1000.0)
                hasher = hashlib.sha256()
                validate_hits(response, args.shards, hasher)
                hashes.add(hasher.hexdigest())
            merge_after, docs_after = index_layout(port)
            if merge_after != merge_before or docs_after != docs_before:
                raise RuntimeError(
                    f"index changed during measurement: merge {merge_before}->{merge_after}, "
                    f"docs {docs_before}->{docs_after}")
            block_median = statistics.median(walls)
            block_medians.append(block_median)
            walls_all.extend(walls)
            sys.stderr.write(f"[repro] {version}/{suffix} block {block_index + 1}: "
                             f"median {block_median:.3f} ms\n")
        if len(hashes) != 1:
            raise RuntimeError("ordered results differ between blocks")
        return {"block_medians": block_medians, "samples": walls_all,
                "result_hash": hashes.pop(), "observed": observed}
    finally:
        sh("docker", "rm", "-f", container)
        sh("docker", "network", "rm", network)
        residue = sh("docker", "ps", "-a", "--filter", f"name=^{container}$",
                     "--format", "{{.Names}}")
        networks = sh("docker", "network", "ls", "--filter", f"name=^{network}$",
                      "--format", "{{.Name}}")
        if (residue.returncode != 0 or networks.returncode != 0
                or residue.stdout.strip() or networks.stdout.strip()):
            sys.stderr.write(f"[repro] teardown {version}/{suffix}: UNKNOWN — failed "
                             f"removal or residue: "
                             f"{(residue.stdout + networks.stdout).strip()[:200]}\n")
        else:
            sys.stderr.write(f"[repro] teardown {version}/{suffix}: owned "
                             f"container/network removed; residue=NONE\n")


def run_version(version, args):
    """Two containers for one version: the release default ceiling vs a node-startup
    128. Negative-control versions (1.3.20, 2.11.1) should show ~1.0x."""
    default_run = run_container(version, ENGINES[version], 1024, args, "default")
    capped_run = run_container(version, ENGINES[version], 128, args, "capped128")
    if default_run["result_hash"] != capped_run["result_hash"]:
        raise RuntimeError(f"{version}: ordered results differ between the two ceilings")
    return {"default": default_run, "capped": capped_run}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--versions", default="1.3.20,2.11.1,2.12.0,2.19.0",
                        help="comma-separated OpenSearch versions from: "
                             + ", ".join(ENGINES))
    parser.add_argument("--docs", type=int, default=198_000)
    parser.add_argument("--shards", type=int, default=18)
    parser.add_argument("--heap", default="8g")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--block-warmups", type=int, default=25)
    parser.add_argument("--chunk", type=int, default=5_000)
    parser.add_argument("--segments-per-shard", type=int, default=2)
    args = parser.parse_args()

    versions = [v.strip() for v in args.versions.split(",") if v.strip()]
    unknown = [v for v in versions if v not in ENGINES]
    if unknown:
        print(f"[error] unknown versions {unknown}; choose from {sorted(ENGINES)}",
              flush=True)
        return 2
    if math.gcd(args.docs, MULTIPLIER) != 1:
        print(f"[error] --docs {args.docs} must be coprime with {MULTIPLIER} "
              f"(use a value not divisible by it), or every rank collides", flush=True)
        return 2
    if args.docs < 4 * PAGE_SIZE or args.shards < 1 or args.samples < 30 \
            or args.block_warmups < 0 or args.chunk < 1 or args.segments_per_shard < 1:
        print("[error] invalid arguments (docs >= 1000, samples >= 30, positive "
              "shards/chunk/segments)", flush=True)
        return 2

    if sh("docker", "info").returncode != 0:
        print("[error] docker daemon unavailable; start Docker Desktop / the daemon first",
              flush=True)
        return 2

    sys.stderr.write(f"[repro] {args.docs} docs / {args.shards} shards / "
                     f"{args.segments_per_shard}+ segments per shard / "
                     f"versions {versions} / ceiling applied at node startup\n")
    matrix = {}
    errors = {}
    for version in versions:
        try:
            matrix[version] = run_version(version, args)
        except Exception as exc:  # noqa: BLE001 - matrix continues; failures reported
            errors[version] = f"{type(exc).__name__}: {exc}"
            print(f"[error] {version}: {errors[version]}", flush=True)

    print(f"\nquery: one-term filter, sorted by high-cardinality keyword, size {PAGE_SIZE}"
          f" | {args.docs} docs / {args.shards} shards | one boolean clause")
    print(f"{'version':>9s} {'observed':>9s} {'default(1024)':>14s} {'node-128':>10s} "
          f"{'speedup':>8s} {'results':>9s}")
    for version in versions:
        if version in errors:
            print(f"{version:>9s} {'FAILED':>9s}  ({errors[version][:90]})")
            continue
        data = matrix[version]
        cells = {}
        for label in ("default", "capped"):
            cells[label] = statistics.median(data[label]["block_medians"])
        speedup = cells["default"] / cells["capped"]
        identical = data["default"]["result_hash"] == data["capped"]["result_hash"]
        print(f"{version:>9s} {data['default']['observed']:>9s} "
              f"{cells['default']:>11.3f} ms {cells['capped']:>7.3f} ms {speedup:>7.2f}x "
              f"{'identical' if identical else 'DIFFER':>9s}"
              f"  blocks {data['default']['block_medians']}/{data['capped']['block_medians']}")
    print("\nexpected: 1.3.20 and 2.11.1 ~1.0x (no competitive-iterator coupling or "
          "MAX_TERMS still 128 — negative controls); 2.12.0 and 2.19.0 slow at the "
          "release default and restored at a node-applied 128.")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
