#!/usr/bin/env python3
"""Minimal synthetic keyword-sort reproduction. Docker + Python stdlib; no lab data.

One version per invocation; four fresh JVMs in 1024,128,128,1024 order.
See README.md for scope, prerequisites, interpretation and provenance.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

VERSIONS = {"1.3.20": "8.10.1", "2.11.1": "9.7.0", "2.12.0": "9.9.2", "2.19.0": "9.12.1"}
IMAGE_DIGESTS = {
    "1.3.20": "7c544a7cb02753c5bb43138c7a499b0e597256c90d8a9dd390c976e58516c92e",
    "2.11.1": "512d52a7a21c990f7dc3c6e4264aa61cbae6ead7a167425438858d86628e70ac",
    "2.12.0": "40a130ec32fa38613761ed3b84fd8d7051f267cda2ab12667b649f58f22e9218",
    "2.19.0": "c9345304e5bec78255a08573457f724eaea99f723d7c454e6131b473b4acd290",
}
INDEX, PAGE_SIZE, MULTIPLIER = "prune-repro", 250, 104729
SETTING = "indices.query.bool.max_clause_count"
QUERY = {
    "size": PAGE_SIZE, "version": True,
    "query": {"bool": {"filter": [{"term": {"tenant_id": "tenant-a"}}]}},
    "sort": [{"item_key": "asc"}, {"market_id": "asc"}],
    "_source": {"excludes": ["source_records.*"]},
}
DEADLINE = float("inf")


def remaining(cap=60):
    seconds = min(cap, DEADLINE - time.monotonic())
    if seconds <= 0:
        raise TimeoutError("benchmark work deadline exceeded")
    return seconds


def docker(*args, timeout=60):
    result = subprocess.run(["docker", *args], text=True, capture_output=True,
                            timeout=remaining(timeout), check=False)
    if result.returncode:
        raise RuntimeError(f"docker {' '.join(args[:3])}: {result.stderr[-2000:]}")
    return result.stdout.strip()


def http(port, method, path, body=None, timeout=60):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=remaining(timeout)) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} {path}: {exc.read()[:1000]!r}") from exc


def ready(port, index=None):
    end = min(DEADLINE, time.monotonic() + 180)
    path = "/_cluster/health" + (f"/{index}?wait_for_status=green&timeout=2s" if index else "")
    while time.monotonic() < end:
        try:
            response = http(port, "GET", path, timeout=3)
            if index is None and response.get("status") in ("yellow", "green"):
                return
            if index and response.get("status") == "green" and response["unassigned_shards"] == 0:
                return
        except (OSError, RuntimeError):
            pass
        time.sleep(1)
    raise TimeoutError(f"OpenSearch readiness failed: {index or 'node'}")


def document(rank):
    return {"item_key": f"item-{rank:09d}", "market_id": rank % 16, "tenant_id": "tenant-a"}


def fixture(port, args):
    http(port, "PUT", f"/{INDEX}", {
        "settings": {"number_of_shards": args.shards, "number_of_replicas": 0,
                     "refresh_interval": "-1"},
        "mappings": {"properties": {"item_key": {"type": "keyword"},
                     "market_id": {"type": "long"}, "tenant_id": {"type": "keyword"}}}})
    ready(port, INDEX)
    chunks = math.ceil(args.docs / args.chunk)
    refresh_every = max(1, chunks // 2)
    for chunk, start in enumerate(range(0, args.docs, args.chunk), 1):
        lines = []
        for ordinal in range(start, min(start + args.chunk, args.docs)):
            rank = ordinal * MULTIPLIER % args.docs
            lines.extend([json.dumps({"index": {"_index": INDEX, "_id": f"item-{rank:09d}"}}),
                          json.dumps(document(rank))])
        req = urllib.request.Request(f"http://127.0.0.1:{port}/_bulk",
                                     data=("\n".join(lines) + "\n").encode(), method="POST",
                                     headers={"Content-Type": "application/x-ndjson"})
        with urllib.request.urlopen(req, timeout=remaining(120)) as response:
            result = json.load(response)
        if result.get("errors") or len(result.get("items", [])) != len(lines) // 2:
            raise RuntimeError("bulk indexing failed")
        if chunk % refresh_every == 0:
            http(port, "POST", f"/{INDEX}/_refresh")
    http(port, "POST", f"/{INDEX}/_refresh")
    # Remain refresh-disabled: no writes during timing. Never force-merge.
    if http(port, "GET", f"/{INDEX}/_count")["count"] != args.docs:
        raise RuntimeError("fixture count mismatch")
    ready(port, INDEX)


def validate(response, shards):
    info = response.get("_shards", {})
    if response.get("timed_out") is not False or info.get("total") != shards \
            or info.get("successful") != shards or info.get("failed") != 0 \
            or info.get("skipped", 0) != 0:
        raise RuntimeError("search timeout or incomplete shard coverage")
    hits = response.get("hits", {}).get("hits", [])
    if len(hits) != PAGE_SIZE:
        raise RuntimeError("wrong hit count")
    rows = [[hit.get("_id"), hit.get("sort"), hit.get("_version"), hit.get("_source")]
            for hit in hits]
    oracle = [[f"item-{rank:09d}", [f"item-{rank:09d}", rank % 16], 1, document(rank)]
              for rank in range(PAGE_SIZE)]
    if rows != oracle:
        raise RuntimeError("ordered ID/sort/version/source oracle mismatch")
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def layout(port):
    stats = http(port, "GET", f"/{INDEX}/_stats/docs,merge,segments")["indices"][INDEX]["primaries"]
    segments = http(port, "GET", f"/{INDEX}/_segments")["indices"][INDEX]["shards"]
    return {"docs": stats["docs"], "merges_total": stats["merges"]["total"],
            "merges_current": stats["merges"]["current"],
            "segments": {shard: sorted(copy["segments"].keys())
                         for shard, copies in segments.items() for copy in copies
                         if copy["routing"]["primary"]}}


def settings(port, ceiling):
    nodes = http(port, "GET", "/_nodes/settings?flat_settings=true")["nodes"]
    if len(nodes) != 1 or any(int(n["settings"].get(SETTING, -1)) != ceiling for n in nodes.values()):
        raise RuntimeError("node startup clause ceiling readback mismatch")
    cluster = http(port, "GET", "/_cluster/settings?flat_settings=true")
    if any(SETTING in cluster.get(layer, {}) for layer in ("persistent", "transient")):
        raise RuntimeError("unexpected cluster override")


def cell(args, image, ceiling, replicate, output):
    """Only returned immutable container IDs may be started or removed."""
    owner = uuid.uuid4().hex
    cid = None
    record = {"ceiling": ceiling, "replicate": replicate, "samples": [], "took_ms": [],
              "block_medians": [], "cleanup": "unknown"}
    output["cells"].append(record)
    try:
        cid = docker("create", "--name", f"keyword-repro-{owner}", "--label", f"repro.owner={owner}",
                     "--cpus", "2", "--memory", "5g", "--memory-swap", "5g", "--pids-limit", "512",
                     "--ulimit", "nofile=65536:65536", "-p", "127.0.0.1::9200",
                     "-e", f"OPENSEARCH_JAVA_OPTS=-Xms{args.heap} -Xmx{args.heap} -XX:ActiveProcessorCount=2",
                     "-e", "discovery.type=single-node", "-e", "DISABLE_SECURITY_PLUGIN=true",
                     "-e", "DISABLE_INSTALL_DEMO_CONFIG=true", "-e", f"{SETTING}={ceiling}", image["Id"])
        if len(cid) != 64 or any(c not in "0123456789abcdef" for c in cid):
            cid = None
            raise RuntimeError("container creation returned ambiguous ownership; no name-based cleanup")
        record["container_id"] = cid
        inspect = json.loads(docker("inspect", cid))[0]
        if inspect["Config"]["Labels"].get("repro.owner") != owner or inspect["Image"] != image["Id"]:
            raise RuntimeError("container identity mismatch")
        docker("start", cid)
        port = int(docker("port", cid, "9200/tcp").splitlines()[0].rsplit(":", 1)[1])
        ready(port)
        version = http(port, "GET", "/")["version"]
        if version["number"] != args.version or version["lucene_version"] != VERSIONS[args.version]:
            raise RuntimeError(f"unexpected engine identity: {version}")
        settings(port, ceiling)
        jvm = next(iter(http(port, "GET", "/_nodes/jvm")["nodes"].values()))["jvm"]
        record["identity"] = {"version": version, "jvm": jvm, "image": image}
        fixture(port, args)
        for block in range(2):
            for _ in range(args.block_warmups):
                validate(http(port, "POST", f"/{INDEX}/_search", QUERY), args.shards)
            before = layout(port)
            if before["docs"] != {"count": args.docs, "deleted": 0} or before["merges_current"]:
                raise RuntimeError("fixture not quiescent before measurement")
            if block == 0:
                record["layout_before"] = before
            elif before != record["layout_after"]:
                raise RuntimeError("index changed between measurement blocks")
            settings(port, ceiling)
            walls = []
            for _ in range(args.samples):
                t0 = time.perf_counter()
                response = http(port, "POST", f"/{INDEX}/_search", QUERY)
                wall = (time.perf_counter() - t0) * 1000
                digest = validate(response, args.shards)
                if record.get("result_hash", digest) != digest:
                    raise RuntimeError("result drift")
                record["result_hash"] = digest
                walls.append(wall)
                record["samples"].append(wall)
                record["took_ms"].append(response["took"])
            after = layout(port)
            if before != after:
                raise RuntimeError("index layout/merge/doc counters changed during measurement")
            settings(port, ceiling)
            record["layout_after"] = after
            record["block_medians"].append(statistics.median(walls))
            print(f"{args.version} ceiling={ceiling} pair={replicate} block={block+1}: "
                  f"{record['block_medians'][-1]:.3f} ms", flush=True)
    except BaseException:
        if cid:
            try:
                record["logs_tail"] = docker("logs", "--tail", "30", cid)[-6000:]
            except Exception:
                pass
        raise
    finally:
        # Cleanup has its own bounded reserve even if the work deadline expired.
        global DEADLINE
        prior = DEADLINE
        DEADLINE = time.monotonic() + 60
        try:
            if cid:
                inspect = json.loads(docker("inspect", cid, timeout=10))[0]
                if inspect["Id"] != cid or inspect["Config"]["Labels"].get("repro.owner") != owner:
                    raise RuntimeError("cleanup ownership unknown; refusing removal")
                docker("rm", "-f", "-v", cid, timeout=30)
                remaining_ids = docker("ps", "-aq", "--no-trunc", "--filter", f"id={cid}", timeout=10)
                if remaining_ids:
                    raise RuntimeError("owned container residue after removal")
                record["cleanup"] = "clean"
        finally:
            DEADLINE = prior


def interrupted(signum, frame):
    raise KeyboardInterrupt(f"signal {signum}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=VERSIONS, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--docs", type=int, default=198000)
    parser.add_argument("--shards", type=int, default=18)
    parser.add_argument("--heap", choices=("1g", "2g", "3g"), default="2g")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--block-warmups", type=int, default=100)
    parser.add_argument("--chunk", type=int, default=5000)
    parser.add_argument("--max-seconds", type=int, default=780)
    args = parser.parse_args()
    if args.docs < 1000 or math.gcd(args.docs, MULTIPLIER) != 1 or args.shards < 1 \
            or args.samples < 30 or args.block_warmups < 0 or args.chunk < 1 \
            or not 120 <= args.max_seconds <= 1800:
        parser.error("invalid fixture, sample, warmup or deadline parameters")
    args.output.mkdir(parents=True, exist_ok=False)
    global DEADLINE
    DEADLINE = time.monotonic() + args.max_seconds - 60
    started = time.monotonic()
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    result = {"schema": 1, "version": args.version, "status": "invalid", "error": None,
              "source_sha": os.environ.get("GITHUB_SHA", "local-uncommitted"),
              "run_url": (f"https://github.com/{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
                          f"{os.environ['GITHUB_RUN_ID']}" if "GITHUB_RUN_ID" in os.environ else "local"),
              "parameters": {k: v for k, v in vars(args).items() if k not in ("version", "output")},
              "query": QUERY, "host": {"platform": platform.platform(), "cpus": os.cpu_count()},
              "cells": []}
    try:
        # Same cooperative lock as the source lab. CI jobs have isolated VMs.
        with open("/tmp/opensearch-regression-lab.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            image_tag = f"opensearchproject/opensearch:{args.version}"
            image_ref = f"opensearchproject/opensearch@sha256:{IMAGE_DIGESTS[args.version]}"
            docker("pull", image_ref, timeout=240)
            full_image = json.loads(docker("image", "inspect", image_ref))[0]
            image = {key: full_image[key] for key in ("Id", "RepoDigests", "Architecture", "Os")}
            image["tag"] = image_tag
            image["pinned_reference"] = image_ref
            if image["Architecture"] != "amd64" or not image["RepoDigests"]:
                raise RuntimeError("requires a digest-resolved linux/amd64 release image")
            for ceiling, replicate in ((1024, 1), (128, 1), (128, 2), (1024, 2)):
                cell(args, image, ceiling, replicate, result)
            if len({c["result_hash"] for c in result["cells"]}) != 1:
                raise RuntimeError("result mismatch across fresh JVMs")
            result["status"] = "valid"
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(result["error"], file=sys.stderr)
    finally:
        result["elapsed_seconds"] = time.monotonic() - started
        (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    sys.exit(main())
