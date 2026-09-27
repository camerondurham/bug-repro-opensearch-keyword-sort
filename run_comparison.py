#!/usr/bin/env python3
"""Run three fixed local comparison matrices and publish their report."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
REPRO = ROOT / "repro.py"
REPORT = ROOT / "report.py"
REFERENCE = ROOT / "results" / "raw"
GENERATOR = "run_comparison.py"
VERSIONS = ("1.3.20", "2.11.1", "2.12.0", "2.19.0", "3.8.0")
ORDERS = (VERSIONS, tuple(reversed(VERSIONS)), ("2.12.0", "2.19.0", "3.8.0", "1.3.20", "2.11.1"))


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git_snapshot():
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout
    if status:
        raise RuntimeError("tracked checkout is not clean")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        capture_output=True, check=True,
    ).stdout.strip()


def child_env(source_sha):
    env = os.environ.copy()
    env["GITHUB_SHA"] = source_sha
    env.pop("GITHUB_RUN_ID", None)
    env.pop("GITHUB_REPOSITORY", None)
    return env


def run_command(command, env):
    print("$ " + " ".join(str(part) for part in command), flush=True)
    return subprocess.run(command, cwd=ROOT, env=env, check=True)


def _resolved(path):
    return Path(os.path.abspath(path)).resolve(strict=False)


def _inside(path, directory):
    return path == directory or directory in path.parents


def validate_destination(path, replace):
    """Validate without following the destination itself before checking it."""
    path = Path(path)
    if path.is_symlink():
        raise ValueError("output destination must not be a symlink")
    resolved = _resolved(path)
    root = ROOT.resolve()
    git_dir = (ROOT / ".git").resolve(strict=False)
    results = (ROOT / "results").resolve(strict=False)
    protected = (git_dir, results, REFERENCE.resolve(strict=False))
    if resolved == root or resolved in root.parents:
        raise ValueError("output destination may not be the repository or an ancestor")
    if any(_inside(resolved, item) or _inside(item, resolved) for item in protected):
        raise ValueError("output destination overlaps protected repository data")
    exists = path.exists()
    if exists and not replace:
        raise FileExistsError(f"output already exists: {path}")
    if exists and not path.is_dir():
        raise ValueError("replacement destination must be a directory")
    if exists:
        try:
            metadata = json.loads((path / "host.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("--replace requires a wrapper-owned output (host.json)") from exc
        if metadata.get("generator") != GENERATOR:
            raise ValueError("--replace requires a wrapper-owned output")
    return exists, os.stat(path, follow_symlinks=False) if exists else None


def host_details():
    cpu_fields = {}
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if ":" in line:
                key, value = (part.strip() for part in line.split(":", 1))
                if key.lower() in {"model name", "hardware"} and value:
                    cpu_fields[key.lower()] = value
    except OSError:
        pass
    cpu_model = cpu_fields.get("model name") or cpu_fields.get("hardware")
    ram_bytes = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                ram_bytes = int(line.split()[1]) * 1024
                break
    except (OSError, ValueError, IndexError):
        pass
    return {
        "os": platform.system() or None,
        "kernel": platform.release() or None,
        "platform": platform.platform() or None,
        "cpu_count": os.cpu_count(),
        "cpu_model": cpu_model,
        "ram_bytes": ram_bytes,
    }


def write_metadata(report_dir, source_sha, started_at, elapsed):
    finished_at = utc_now()
    metadata = {
        "generator": GENERATOR,
        "source_sha": source_sha,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_seconds": elapsed,
        **host_details(),
    }
    (report_dir / "host.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def _guard_destination(output, existed, original_stat):
    if output.is_symlink():
        raise RuntimeError("output destination changed into a symlink")
    if existed:
        if not output.is_dir() or not output.joinpath("host.json").is_file():
            raise RuntimeError("replacement destination changed or is no longer wrapper-owned")
        current = os.stat(output, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (original_stat.st_dev, original_stat.st_ino):
            raise RuntimeError("replacement destination was swapped while running")
        try:
            if json.loads((output / "host.json").read_text(encoding="utf-8")).get("generator") != GENERATOR:
                raise RuntimeError("replacement destination is no longer wrapper-owned")
        except (OSError, ValueError) as exc:
            raise RuntimeError("replacement destination is no longer wrapper-owned") from exc
    elif output.exists():
        raise RuntimeError("output appeared while running; refusing to overwrite it")


def publish(staging, output, existed, original_stat):
    _guard_destination(output, existed, original_stat)
    report = staging / "report"
    if not report.is_dir():
        raise RuntimeError("report output is missing")
    if existed:
        previous = staging / "previous"
        os.rename(output, previous)
        try:
            os.rename(report, output)
        except BaseException:
            try:
                os.rename(previous, output)
            except BaseException as rollback_error:
                raise RuntimeError("publication failed and rollback failed") from rollback_error
            raise
    else:
        os.rename(report, output)
    try:
        shutil.rmtree(staging)
    except (OSError, KeyboardInterrupt) as exc:
        print(f"Warning: published report but could not clean staging {staging}: {exc}",
              file=sys.stderr, flush=True)


def run(output, replace=False):
    started_clock = time.monotonic()
    started_at = utc_now()
    staging = None
    try:
        source_sha = git_snapshot()
        output = Path(output)
        existed, original_stat = validate_destination(output, replace)
        # Publish at the resolved location after rejecting a symlink target.
        output = _resolved(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
        env = child_env(source_sha)
        for number, order in enumerate(ORDERS, 1):
            matrix = staging / f"local-{number}"
            for version in order:
                print(f"Measuring local-{number} {version}", flush=True)
                run_command([
                    sys.executable, str(REPRO), "--version", version,
                    "--output", str(matrix / version), "--max-seconds", "780",
                ], env)
        run_command([
            sys.executable, str(REPORT), "--compare",
            f"local-1={staging / 'local-1'}",
            f"local-2={staging / 'local-2'}",
            f"local-3={staging / 'local-3'}",
            "--reference", f"actions={REFERENCE}",
            "--output", str(staging / "report"),
        ], env)
        if git_snapshot() != source_sha:
            raise RuntimeError("tracked checkout or HEAD changed during comparison")
        write_metadata(staging / "report", source_sha, started_at, time.monotonic() - started_clock)
        publish(staging, output, existed, original_stat)
        print(f"Published report: {output / 'report.html'}", flush=True)
        return 0
    except BaseException as exc:
        print(f"Comparison failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        if staging is not None and staging.exists():
            print(f"Evidence retained at: {staging}", file=sys.stderr, flush=True)
        return 130 if isinstance(exc, KeyboardInterrupt) else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="machine report directory to publish")
    parser.add_argument("--replace", action="store_true",
                        help="replace an existing output previously generated by this runner")
    args = parser.parse_args(argv)
    return run(args.output, args.replace)


if __name__ == "__main__":
    raise SystemExit(main())
