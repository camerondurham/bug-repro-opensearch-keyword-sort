#!/usr/bin/env python3
"""Small, fail-closed reporter for the keyword-sort reproduction."""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
import statistics
import tempfile
from pathlib import Path

HISTORICAL_VERSIONS = ("1.3.20", "2.11.1", "2.12.0", "2.19.0")
VERSIONS = (*HISTORICAL_VERSIONS, "3.8.0")
ORDER = ((1024, 1), (128, 1), (128, 2), (1024, 2))
COLORS = {1024: "#d95f02", 128: "#1b75bc"}


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def med(values):
    return statistics.median(values)


def esc(value):
    return html.escape(str(value), quote=True)


def svg_text(x, y, text, size=12, anchor="start", fill="#222", weight="normal"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="sans-serif" '
            f'font-size="{size}px" text-anchor="{anchor}" fill="{fill}" '
            f'font-weight="{weight}">{esc(text)}</text>')


def read_results(root):
    found = []
    # Actions artifacts use */result.json; committed evidence uses raw/<version>.json.
    paths = ([root] if root.is_file() else
             sorted(set(root.rglob("result.json")) | set(root.glob("[0-9]*.json")) |
                    set(root.glob("raw/*.json"))))
    for path in paths:
        item = {"path": path, "data": None, "error": None}
        try:
            item["data"] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # Keep malformed evidence visible in the report.
            item["error"] = f"cannot parse JSON: {exc}"
        found.append(item)
    return found


def validate_record(item):
    d, errors = item.get("data"), []
    if item.get("error"):
        return [item["error"]]
    if not isinstance(d, dict):
        return ["top level is not an object"]
    for key in ("schema", "version", "source_sha", "run_url", "parameters", "query", "status", "error", "cells"):
        if key not in d:
            errors.append(f"missing top-level field {key}")
    if d.get("schema") != 1:
        errors.append("schema is not 1")
    if d.get("version") not in VERSIONS:
        errors.append("unknown version")
    if not isinstance(d.get("source_sha"), str) or not d["source_sha"]:
        errors.append("source_sha is missing")
    if not isinstance(d.get("run_url"), str) or not d["run_url"]:
        errors.append("run_url is missing")
    if d.get("status") != "valid":
        errors.append("status is not valid")
    if d.get("error") is not None and not isinstance(d.get("error"), str):
        errors.append("error is neither null nor a string")
    if d.get("status") == "valid" and d.get("error") is not None:
        errors.append("valid result has a non-null error")
    p = d.get("parameters")
    samples_per_block = None
    if not isinstance(p, dict):
        errors.append("parameters is not an object")
    else:
        # Match the runner's admitted CLI values, not just the published defaults.
        for key, minimum in (("docs", 1000), ("shards", 1), ("samples", 30),
                             ("block_warmups", 0), ("chunk", 1), ("max_seconds", 120)):
            value = p.get(key)
            if type(value) is not int or value < minimum:
                errors.append(f"parameters.{key} must be an integer >= {minimum}")
        if type(p.get("docs")) is int and math.gcd(p["docs"], 104729) != 1:
            errors.append("parameters.docs must be coprime with 104729")
        if p.get("heap") not in ("1g", "2g", "3g"):
            errors.append("parameters.heap is not an admitted runner heap")
        if type(p.get("max_seconds")) is int and p["max_seconds"] > 1800:
            errors.append("parameters.max_seconds exceeds 1800")
        if type(p.get("samples")) is int and p["samples"] >= 30:
            samples_per_block = p["samples"]
    expected_samples = 2 * samples_per_block if samples_per_block is not None else None
    if not isinstance(d.get("query"), dict):
        errors.append("query is not an object")
    cells = d.get("cells")
    if not isinstance(cells, list) or len(cells) != 4:
        errors.append("cells does not contain exactly four entries")
        return errors
    for i, (cell, expected) in enumerate(zip(cells, ORDER)):
        if not isinstance(cell, dict):
            errors.append(f"cell {i} is not an object")
            continue
        ceiling, replicate = expected
        if cell.get("ceiling") != ceiling or cell.get("replicate") != replicate:
            errors.append(f"cell {i} is not {ceiling}/{replicate} in the required order")
        blocks, samples, took = cell.get("block_medians"), cell.get("samples"), cell.get("took_ms")
        if not isinstance(blocks, list) or len(blocks) != 2:
            errors.append(f"cell {i} does not have two block medians")
        if not isinstance(samples, list) or len(samples) != expected_samples:
            errors.append(f"cell {i} sample count does not match two declared blocks")
        if not isinstance(took, list) or len(took) != expected_samples:
            errors.append(f"cell {i} took_ms count does not match two declared blocks")
        if isinstance(blocks, list):
            if not all(finite_number(x) and x > 0 for x in blocks):
                errors.append(f"cell {i} has invalid block medians")
        if isinstance(samples, list):
            if not all(finite_number(x) and x > 0 for x in samples):
                errors.append(f"cell {i} has invalid samples")
        if isinstance(took, list):
            if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in took):
                errors.append(f"cell {i} has invalid took_ms values")
        if (isinstance(blocks, list) and len(blocks) == 2 and isinstance(samples, list)
                and len(samples) == expected_samples and all(finite_number(x) and x > 0 for x in blocks)
                and all(finite_number(x) and x > 0 for x in samples)):
            actual = [med(samples[:samples_per_block]), med(samples[samples_per_block:])]
            if any(not math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-7) for a, b in zip(blocks, actual)):
                errors.append(f"cell {i} block medians do not match samples")
        if not isinstance(cell.get("result_hash"), str) or not cell["result_hash"]:
            errors.append(f"cell {i} has no result_hash")
        identity = cell.get("identity")
        if not isinstance(identity, dict):
            errors.append(f"cell {i} has no identity")
        else:
            iv = identity.get("version")
            if not isinstance(iv, dict) or not isinstance(iv.get("number"), str) or not isinstance(iv.get("lucene_version"), str):
                errors.append(f"cell {i} has incomplete version identity")
            elif iv["number"] != d.get("version"):
                errors.append(f"cell {i} identity version does not match returned version")
            for key in ("jvm", "image"):
                if not isinstance(identity.get(key), dict):
                    errors.append(f"cell {i} identity.{key} is not an object")
        for key in ("layout_before", "layout_after"):
            if not isinstance(cell.get(key), dict):
                errors.append(f"cell {i} has no {key}")
        if cell.get("cleanup") != "clean":
            errors.append(f"cell {i} cleanup is not clean")
    return errors


def validate_all(items, versions=VERSIONS):
    errors = []
    by_version = {}
    for item in items:
        d = item.get("data")
        version = d.get("version") if isinstance(d, dict) else None
        if version in VERSIONS:
            by_version.setdefault(version, []).append(item)
        item["errors"] = validate_record(item)
    for version in versions:
        if len(by_version.get(version, [])) != 1:
            errors.append(f"expected exactly one result for {version}, found {len(by_version.get(version, []))}")
    for version, group in by_version.items():
        if len(group) > 1:
            errors.append(f"duplicate result for {version}")
    chosen = {v: by_version[v][0] for v in versions if len(by_version.get(v, [])) == 1}
    for item in items:
        d = item.get("data")
        version = d.get("version") if isinstance(d, dict) else None
        if version not in VERSIONS:
            errors.extend(f"{item['path']}: {e}" for e in (item.get("errors") or ["unknown or malformed result"]))
    for v, item in chosen.items():
        errors.extend(f"{v}: {e}" for e in item["errors"])
    if len(chosen) == len(versions) and all(not chosen[v]["errors"] for v in versions):
        first = chosen[versions[0]]["data"]
        for v in versions[1:]:
            d = chosen[v]["data"]
            for key in ("parameters", "query", "source_sha", "run_url"):
                if d.get(key) != first.get(key):
                    errors.append(f"{key} differs between releases")
        hashes = {c["result_hash"] for v in versions for c in chosen[v]["data"]["cells"]}
        if len(hashes) != 1:
            errors.append("result_hash differs across cells or releases")
    return chosen, errors


def cell_median(cell, field="samples"):
    values = cell[field]
    n = len(values) // 2
    return med([med(values[:n]), med(values[n:])])


def pair_info(d, field="samples"):
    cells = d["cells"]
    pairs = []
    for default, control in ((cells[0], cells[1]), (cells[3], cells[2])):
        a, b = cell_median(default, field), cell_median(control, field)
        pairs.append({"default": a, "ceiling_128": b, "ratio": a / b if b else None})
    return pairs


def ratio_text(value):
    return f"{value:.3f}×" if value is not None else "n/a (zero denominator)"


def print_pairs(d):
    print(f"{d['version']}: runner validation (recorded)={d['status']}; paired 1024 / 128 ratios")
    for n, (client, took) in enumerate(zip(pair_info(d), pair_info(d, "took_ms")), 1):
        print(f"  pair {n}: client {ratio_text(client['ratio'])} "
              f"({client['default']:.3f} / {client['ceiling_128']:.3f} ms); "
              f"server took {ratio_text(took['ratio'])} "
              f"({took['default']:.3f} / {took['ceiling_128']:.3f} ms)")
    print("Full-matrix verdict not assessed by a single-version run.")


def render_matrix(chosen, versions=VERSIONS):
    width, height, left, right, top, bottom = 1200, 560, 90, 1160, 100, 475
    values = []
    for v in versions:
        d = chosen.get(v, {}).get("data") if isinstance(chosen.get(v), dict) else None
        if d and not chosen[v].get("errors"):
            values.extend(cell_median(c) for c in d["cells"])
    ymax = max(values or [1]) * 1.25
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>', svg_text(600, 28, "Keyword-sort latency by clause limit", 18, "middle", weight="bold"),
             svg_text(600, 48, "Client latency for repeated searches of the first page", 11, "middle", fill="#555"),
             svg_text(600, 64, "Compare settings within each release. Each setting was tested in two separately started containers.", 11, "middle", fill="#555")]
    for tick in range(5):
        y = bottom - (bottom - top) * tick / 4
        value = ymax * tick / 4
        parts += [f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#ddd"/>', svg_text(left - 10, y + 4, f"{value:.1f}", 11, "end")]
    parts += [f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#333"/>',
              f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#333"/>',
              svg_text(25, (top + bottom) / 2, "ms", 12, "middle")]
    group_w = (right - left) / len(versions)
    for i, version in enumerate(versions):
        d = chosen.get(version, {}).get("data") if isinstance(chosen.get(version), dict) else None
        gx = left + i * group_w
        parts.append(svg_text(gx + group_w / 2, bottom + 28, version, 13, "middle", weight="bold"))
        for j, ceiling in enumerate((1024, 128)):
            cell_indexes = (0, 3) if ceiling == 1024 else (1, 2)
            x = gx + group_w * .22 + j * group_w * .28
            if not d or chosen[version].get("errors"):
                continue
            vals = [cell_median(d["cells"][n]) for n in cell_indexes]
            value = med(vals)
            bar_h = (bottom - top) * value / ymax
            parts += [f'<rect x="{x:.1f}" y="{bottom-bar_h:.1f}" width="55" height="{bar_h:.1f}" fill="{COLORS[ceiling]}"/>',
                      svg_text(x + 27.5, bottom - bar_h - 9, f"{vals[0]:.1f} / {vals[1]:.1f}", 10, "middle"),
                      svg_text(x + 27.5, bottom + 14, str(ceiling), 10, "middle")]
    parts += [f'<rect x="400" y="78" width="14" height="14" fill="{COLORS[1024]}"/>', svg_text(420, 90, "Default limit: 1024", 11),
              f'<rect x="650" y="78" width="14" height="14" fill="{COLORS[128]}"/>', svg_text(670, 90, "Lowered limit: 128", 11), '</svg>']
    return "\n".join(parts)


def render_requests(chosen, versions=VERSIONS):
    width, panel_h, height = 1200, 275, len(versions) * 275 + 45
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="white"/>', svg_text(600, 25, "All measured requests by release", 18, "middle", weight="bold"),
             svg_text(600, 45, "Each section is a separate OpenSearch container. Dashed lines divide its two measurement blocks.", 11, "middle", fill="#555")]
    plot_left, plot_right = 90, 1160
    all_points = []
    for version in versions:
        item = chosen.get(version)
        if item and not item.get("errors") and isinstance(item.get("data"), dict):
            for cell in item["data"].get("cells", []):
                all_points.extend(x for x in cell.get("samples", []) if finite_number(x) and x > 0)
    ymax = max(all_points or [1]) * 1.12
    for row, version in enumerate(versions):
        y0, top, bottom = row * panel_h + 100, row * panel_h + 100, row * panel_h + 273
        item = chosen.get(version)
        d = item.get("data") if item else None
        parts += [svg_text(90, y0 - 20, f"{version} request samples", 14, weight="bold"),
                  svg_text(1160, y0 - 20, f"N={8 * d['parameters']['samples']}" if d and not item.get("errors") else "incomplete / invalid", 11, "end", fill="#a00" if not d or item.get("errors") else "#555"),
                  f'<line x1="{plot_left}" y1="{bottom}" x2="{plot_right}" y2="{bottom}" stroke="#333"/>',
                  f'<line x1="{plot_left}" y1="{top}" x2="{plot_left}" y2="{bottom}" stroke="#333"/>',
                  svg_text(20, (top + bottom) / 2, "ms", 11, "middle")]
        for tick in (0, .5, 1):
            y = bottom - (bottom - top) * tick
            parts += [f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_right}" y2="{y:.1f}" stroke="#eee"/>', svg_text(plot_left - 8, y + 4, f"{ymax*tick:.0f}", 9, "end")]
        if not d or item.get("errors"):
            parts.append(svg_text(600, (top + bottom) / 2, "missing or invalid result for this release", 13, "middle", fill="#a00"))
            continue
        for cell_no, cell in enumerate(d.get("cells", [])):
            x0 = plot_left + (plot_right - plot_left) * cell_no / 4
            x1 = plot_left + (plot_right - plot_left) * (cell_no + 1) / 4
            parts += [f'<line x1="{x0:.1f}" y1="{top}" x2="{x0:.1f}" y2="{bottom}" stroke="#777" stroke-width="2"/>',
                      svg_text((x0+x1)/2, bottom + 18, f"Container {cell_no+1} ({cell.get('ceiling', '?')})", 9, "middle")]
            mid = (x0 + x1) / 2
            parts.append(f'<line x1="{mid:.1f}" y1="{top}" x2="{mid:.1f}" y2="{bottom}" stroke="#999" stroke-dasharray="3,3"/>')
            samples = cell.get("samples", [])
            pts = []
            for n, value in enumerate(samples):
                if not finite_number(value) or value <= 0:
                    continue
                x = x0 + (n + .5) * (x1 - x0) / len(samples)
                y = bottom - (bottom - top) * value / ymax
                pts.append((x, y))
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.7" fill="{COLORS.get(cell.get("ceiling"), "#777")}"/>')
            if pts:
                parts.append('<polyline fill="none" stroke="%s" stroke-width="0.7" opacity=".35" points="%s"/>' %
                             (COLORS.get(cell.get("ceiling"), "#777"), " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)))
    parts += [f'<rect x="550" y="{height-25}" width="12" height="12" fill="{COLORS[1024]}"/>', svg_text(568, height-15, "Default limit: 1024", 10),
              f'<rect x="700" y="{height-25}" width="12" height="12" fill="{COLORS[128]}"/>', svg_text(718, height-15, "Lowered limit: 128", 10),
              f'<line x1="850" y1="{height-19}" x2="875" y2="{height-19}" stroke="#777" stroke-width="2"/>', svg_text(882, height-15, "container boundary", 10),
              f'<line x1="1030" y1="{height-19}" x2="1055" y2="{height-19}" stroke="#999" stroke-dasharray="3,3"/>', svg_text(1062, height-15, "block boundary", 10), '</svg>']
    return "\n".join(parts)


def summary_and_metrics(chosen, errors, versions=VERSIONS):
    valid = not errors
    ratios, server = {}, {}
    runner_status = {v: chosen[v]["data"].get("status") for v in versions if v in chosen}
    for version in versions:
        item = chosen.get(version)
        if item and not item.get("errors"):
            ratios[version] = pair_info(item["data"])
            server[version] = pair_info(item["data"], "took_ms")
    full_matrix = tuple(versions) in (VERSIONS, HISTORICAL_VERSIONS) and len(chosen) == len(versions)
    reproduced = valid and full_matrix and all(r["ratio"] >= 1.25 for v in ("2.12.0", "2.19.0") for r in ratios[v]) and all(
        0.8 <= r["ratio"] <= 1.25 for v in ("1.3.20", "2.11.1") for r in ratios[v])
    outcome = ("INVALID_EVIDENCE" if not valid else "NOT_ASSESSED" if not full_matrix else
               "REPRODUCED" if reproduced else "NOT_REPRODUCED")
    lines = ["# Boolean-clause ceiling changes keyword-sorted query latency", "",
             "**Runner validation (recorded):** " + ", ".join(f"{v}={runner_status.get(v, 'missing')}" for v in versions),
             f"**Reporter evidence checks / recomputation:** {'PASS' if valid else 'FAIL'}",
             f"**Historical-boundary performance outcome:** **{outcome}**", "",
             "Reported releases: " + ", ".join(versions) + ".", "",
             "Each block value is a median of its retained samples. A container result is the median of its two block medians. "
             "Tables show the median of the two container results for each setting, followed by both results in parentheses. "
             "Ratios are 1024 / 128 in the two opposite orders."]
    for title, series in (("Client wall latency", ratios), ("Server `took`", server)):
        lines += ["", f"## {title}", "", "| Version | Default limit 1024 (ms) | Lowered limit 128 (ms) | Pair ratios (1024 / 128) |", "|---|---:|---:|---|"]
        for version in versions:
            rs = series.get(version)
            if rs:
                dvals = [r["default"] for r in rs]
                cvals = [r["ceiling_128"] for r in rs]
                ratios_text = ", ".join(ratio_text(r["ratio"]) for r in rs)
                lines.append(f"| {version} | {med(dvals):.3f} ({dvals[0]:.3f}, {dvals[1]:.3f}) | {med(cvals):.3f} ({cvals[0]:.3f}, {cvals[1]:.3f}) | {ratios_text} |")
            else:
                lines.append(f"| {version} | unavailable | unavailable | unavailable |")
    lines += ["", "Client wall time includes HTTP/JSON decoding, excluding oracle checking. "
              "Server `took` is the returned integer-millisecond server duration, not CPU time; "
              "it excludes client/network overhead. A zero control median gives an undefined (`n/a`) ratio.",
              "", "## Provenance", ""]
    first = next((chosen[v]["data"] for v in versions if v in chosen and isinstance(chosen[v].get("data"), dict)), None)
    lines += [f"- Source SHA: `{first.get('source_sha') if first else 'unavailable'}`", f"- Run: {first.get('run_url') if first else 'unavailable'}"]
    if first and first.get("run_url", "").startswith("https://github.com/"):
        repo_url = first["run_url"].split("/actions/runs/")[0]
        lines += [f"- [Exact benchmark source]({repo_url}/tree/{first['source_sha']})",
                  f"- [Published charts and raw data]({repo_url}/tree/main/results)"]
    lines += ["", "[Matrix chart](matrix.svg) · [Every request](requests.svg) · [Offline HTML report](report.html)",
              "", "Historical-boundary rule: both 2.12.0/2.19.0 pairs ≥1.25×, both 1.3.20/2.11.1 pairs within [0.80, 1.25]. "
              "3.8.0 is measured descriptively, not assumed affected or used to decide that historical verdict. "
              "Default matrix validity requires all five releases; explicit historical replay requires the original four.",
              "", "## Runner validation versus reporter recomputation", "",
              "- The runner performed live response-oracle, settings, index-state, identity and owned-cleanup checks. "
              "Its `status`, hashes, identity/layout snapshots and cleanup markers are retained claims.",
              "- The reporter checks those records' structure, declared sample counts, ABBA labels, recorded version numbers, "
              "clean markers and matching hashes/parameters across the selected releases. It recomputes client/server block medians "
              "and paired ratios from raw timing arrays, and compares client block medians with the recorded values.",
              "- The reporter does not contact Docker/OpenSearch or revalidate live settings/ownership. "
              "Full response bodies and every live readback are not retained; it cannot independently replay the response oracle "
              "or certify that cleanup occurred. This is evidence replay, not a new experiment.",
              "", "### Reporter findings", ""]
    lines += [f"- {e}" for e in errors] or ["- Retained evidence checks and timing recomputation passed."]
    if not full_matrix:
        lines += ["- No historical-boundary verdict: paired single-version results are descriptive."]
    if first and isinstance(first.get("parameters"), dict):
        lines += ["", "Recorded parameters: `" + json.dumps(first["parameters"], sort_keys=True) + "`."]
    lines += ["", "## Limitations", "", "- Bundled JDK versions and hosted VMs are confounded across releases.",
              "- Container CPU limit is 2; heap and sample counts are recorded above (published run: 2 GiB heap).",
              "- Reduced synthetic fixture: keyword `item_key` + long `market_id` sorts; repeated first page only, no pagination.",
              "- Not a production write/cleanup shark-fin reproduction, full traversal, or isolated commit revert.",
              "- Samples are not independent replicates; fresh JVMs and block boundaries are shown separately.",
              "- The 128 setting also limits Boolean/expanded queries; it is not blanket production advice.", ""]
    metrics = {"schema": 1, "versions": list(versions), "valid": valid, "outcome": outcome,
               "errors": errors, "pair_ratios": ratios, "server_took_pair_ratios": server,
               "runner_status": runner_status, "reporter_checks": "PASS" if valid else "FAIL",
               "outcome_scope": "historical_1.x_2.x_boundary"}
    return "\n".join(lines), metrics


def write_report(items, chosen, errors, output, versions=VERSIONS):
    output.mkdir(parents=True, exist_ok=True)
    raw = output / "raw"
    raw.mkdir(exist_ok=True)
    used = {}
    for n, item in enumerate(items, 1):
        d = item.get("data")
        version = d.get("version") if isinstance(d, dict) and d.get("version") in VERSIONS else f"invalid-{n}"
        used[version] = used.get(version, 0) + 1
        suffix = "" if used[version] == 1 else f"-duplicate-{used[version]}"
        destination = raw / f"{version}{suffix}.json"
        if item["path"].resolve() != destination.resolve():
            shutil.copyfile(item["path"], destination)
    matrix = render_matrix(chosen, versions)
    requests = render_requests(chosen, versions)
    summary, metrics = summary_and_metrics(chosen, errors, versions)
    (output / "matrix.svg").write_text(matrix, encoding="utf-8")
    (output / "requests.svg").write_text(requests, encoding="utf-8")
    (output / "summary.md").write_text(summary, encoding="utf-8")
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    rows = []
    for v in versions:
        item = chosen.get(v)
        state = "reporter checks passed" if item and not item.get("errors") else "invalid/missing"
        rs = metrics["pair_ratios"].get(v, [])
        ratio_text = ", ".join(f"{r['ratio']:.3f}" for r in rs) or "unavailable"
        rows.append(f"<tr><td>{esc(v)}</td><td>{esc(state)}</td><td>{esc(ratio_text)}</td></tr>")
    document = """<!doctype html><meta charset="utf-8"><title>Boolean-clause ceiling and keyword-sorted query latency</title>
<style>body{font:14px sans-serif;max-width:1200px;margin:2em auto}svg{width:100%%;height:auto}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:.35em .7em}</style>
<h1>Boolean-clause ceiling changes keyword-sorted query latency</h1><table><tr><th>Version</th><th>Reporter evidence checks</th><th>Client pair ratios (1024 / 128)</th></tr>%s</table><h2>Latency matrix</h2>%s<h2>Requests</h2>%s<pre>%s</pre>""" % ("".join(rows), matrix, requests, esc(summary))
    (output / "report.html").write_text(document, encoding="utf-8")
    return metrics


def run(input_dir, output_dir, version=None, historical_matrix=False):
    versions = (version,) if version else HISTORICAL_VERSIONS if historical_matrix else VERSIONS
    items = read_results(Path(input_dir))
    if version:
        items = [item for item in items if not isinstance(item.get("data"), dict)
                 or item["data"].get("version") not in VERSIONS
                 or item["data"]["version"] == version]
    chosen, errors = validate_all(items, versions)
    metrics = write_report(items, chosen, errors, Path(output_dir), versions)
    print(f"Reporter checks: {metrics['reporter_checks']}; historical-boundary outcome: {metrics['outcome']}")
    if version and not errors:
        print_pairs(chosen[version]["data"])
    return 0 if not errors else 1


def fake_result(version, controls=False):
    medians = ([90, 90], [100, 100], [100, 100], [110, 110]) if controls else ([100, 100], [70, 70], [72, 72], [108, 108])
    cells = []
    for (ceiling, replicate), pair in zip(ORDER, medians):
        samples = [float(pair[0])] * 100 + [float(pair[1])] * 100
        cells.append({"ceiling": ceiling, "replicate": replicate, "block_medians": pair, "samples": samples, "took_ms": [int(pair[0])] * 100 + [int(pair[1])] * 100,
                      "result_hash": "same-result", "identity": {"version": {"number": version, "lucene_version": "9.12.1"}, "jvm": {"version": "21"}, "image": {"digest": "sha256:x"}},
                      "layout_before": {}, "layout_after": {}, "cleanup": "clean"})
    return {"schema": 1, "version": version, "source_sha": "source", "run_url": "https://example.invalid/run", "parameters": {"docs": 198000, "shards": 18, "heap": "2g", "samples": 100, "block_warmups": 100, "chunk": 5000, "max_seconds": 780}, "query": {"query": {"match_all": {}}}, "status": "valid", "error": None, "cells": cells}


def spread(values):
    middle = med(values)
    return {"min": min(values), "median": middle, "max": max(values),
            "relative_range": (max(values) - min(values)) / middle if middle else None}


def comparison_svg(datasets, reference, latency=False):
    labels = list(datasets)
    colors = {label: ("#666666" if label == reference else
                     ("#0072b2", "#d55e00", "#009e73", "#cc79a7", "#56b4e9", "#e69f00")[i])
              for i, label in enumerate(labels)}
    fields = ("default", "ceiling_128") if latency else ("ratio",)
    height = 100 + 390 * len(fields)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1240 {height}">',
             '<rect width="1240" height="100%" fill="white"/>',
             svg_text(620, 25, "Client latency across matrices" if latency else "Paired speedups across matrices", 19, "middle", weight="bold"),
             svg_text(620, 47, "Two points per dataset/version: fresh opposite-order pairs, not independent requests or confidence intervals", 12, "middle")]
    for i, label in enumerate(labels):
        x = 90 + i * 1120 / len(labels)
        parts.append(svg_text(x, 70, label + (" (reference)" if label == reference else ""), 12, fill=colors[label]))
    ymax = max(p[f] for d in datasets.values() for ps in d["pair_ratios"].values()
               for p in ps for f in fields) * 1.15
    for panel, field in enumerate(fields):
        top, bottom = 110 + panel * 390, 410 + panel * 390
        label = {"ratio": "1024 / 128 speedup (×)", "default": "Ceiling 1024 — client ms", "ceiling_128": "Ceiling 128 — client ms"}[field]
        parts.append(svg_text(90, top - 14, label, 13, weight="bold"))
        for tick in range(5):
            y = bottom - (bottom - top) * tick / 4
            parts += [f'<path d="M90 {y:.2f} H1210" stroke="#ddd"/>',
                      svg_text(80, y + 4, f"{ymax * tick / 4:.2f}", 11, "end")]
        if field == "ratio":
            y = bottom - (bottom - top) / ymax
            parts.append(f'<path d="M90 {y:.2f} H1210" stroke="#777" stroke-dasharray="4,4"/>')
        for vi, version in enumerate(VERSIONS):
            group = 1120 / len(VERSIONS)
            parts.append(svg_text(90 + (vi + .5) * group, bottom + 24, version, 13, "middle", weight="bold"))
            for di, name in enumerate(labels):
                x = 90 + vi * group + (di + .5) * group / len(labels)
                for pi, pair in enumerate(datasets[name]["pair_ratios"][version]):
                    value = pair[field]
                    y = bottom - (bottom - top) * value / ymax
                    parts.append(f'<circle cx="{x + (pi * 2 - 1) * 3:.2f}" cy="{y:.2f}" r="4" fill="{colors[name]}" fill-opacity=".8"><title>{esc(name)} {version} pair {pi + 1}: {value:.6f}</title></circle>')
    parts.append('</svg>')
    return "\n".join(parts)


def compare_runs(entries, output_dir, reference=None):
    """Compare whole validated matrices, never pool their request samples."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    errors, selected, datasets, seen = [], {}, {}, set()
    reference_label = None
    all_entries = list(entries) + ([reference] if reference else [])
    if not 2 <= len(entries) <= 6 or len(all_entries) > 6:
        errors.append("comparison requires 2–6 matrices, at most 6 including reference")
    for entry in all_entries:
        label, sep, path = entry.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,47}", label) or label in selected:
            errors.append(f"invalid or duplicate LABEL=INPUT: {entry}")
            continue
        if entry == reference:
            reference_label = label
        items = read_results(Path(path))
        chosen, findings = validate_all(items)
        selected[label] = (items, chosen)
        errors.extend(f"{label}: {e}" for e in findings)
        if findings:
            continue
        identity = tuple(items_v["path"].read_bytes() for items_v in chosen.values())
        if identity in seen:
            errors.append(f"{label}: duplicate evidence is not another repetition")
        seen.add(identity)
        _, metrics = summary_and_metrics(chosen, [])
        first = chosen[VERSIONS[0]]["data"]
        metrics.update(source_sha=first["source_sha"], run_url=first["run_url"], host=first.get("host"))
        datasets[label] = metrics
    if not errors:
        first_chosen = next(iter(selected.values()))[1]
        for label, (_, chosen) in selected.items():
            for v in VERSIONS:
                baseline, current = first_chosen[v]["data"], chosen[v]["data"]
                for key in ("parameters", "query"):
                    if baseline[key] != current[key]:
                        errors.append(f"{label}/{v}: {key} differs across matrices")
                def image_identity(cell):
                    ident = cell["identity"]
                    return (ident["version"]["number"], ident["version"]["lucene_version"],
                            ident["image"].get("Id"), ident["image"].get("pinned_reference"))
                expected = image_identity(baseline["cells"][0])
                if not all(isinstance(x, str) and x for x in expected) or any(
                        image_identity(c) != expected for c in current["cells"]):
                    errors.append(f"{label}/{v}: missing or different frozen engine/image identity")
                if any(c["result_hash"] != baseline["cells"][0]["result_hash"] for c in current["cells"]):
                    errors.append(f"{label}/{v}: oracle hashes differ across matrices")
    if errors:
        (output / "summary.md").write_text("# Matrix comparison — INVALID\n\n" + "\n".join("- " + e for e in errors) + "\n")
        (output / "comparison.json").write_text(json.dumps({"valid": False, "errors": errors}, indent=2) + "\n")
        invalid = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 100">' + svg_text(20, 50, "INVALID comparison — see summary.md", 20) + '</svg>'
        for name in ("ratios.svg", "latency.svg"):
            (output / name).write_text(invalid)
        (output / "report.html").write_text('<!doctype html><meta charset="utf-8"><pre>' + esc((output / "summary.md").read_text()) + '</pre>')
        print("Comparison failed: " + "; ".join(errors))
        return 1
    for label, (items, chosen) in selected.items():
        write_report(items, chosen, [], output / "datasets" / label)
    repetitions = {k: v for k, v in datasets.items() if k != reference_label}
    ranges = {}
    for v in VERSIONS:
        ranges[v] = {"paired_ratio": spread([p["ratio"] for d in repetitions.values() for p in d["pair_ratios"][v]])}
        for key in ("default", "ceiling_128"):
            ranges[v][key] = spread([med([p[key] for p in d["pair_ratios"][v]]) for d in repetitions.values()])
        ranges[v]["spread_flag"] = (ranges[v]["paired_ratio"]["relative_range"] > .15 or
                                    any(ranges[v][key]["relative_range"] > .20 for key in ("default", "ceiling_128")))
    lines = ["# Whole-matrix repeatability comparison", "", "**Retained evidence checks: PASS.** No requests were pooled.",
             "", f"Repetitions: {', '.join(repetitions)}. Reference: {reference_label or 'none'}.",
             "A reference is displayed separately and excluded from repetition spreads. Dataset labels do not establish independent physical hosts.",
             "", "## Client summaries by matrix", "", "| Version | Dataset | 1024 median ms | 128 median ms | Paired client speedups | Paired server `took` speedups |", "|---|---|---:|---:|---|---|"]
    for v in VERSIONS:
        for label, d in datasets.items():
            ps = d["pair_ratios"][v]
            lines.append(f"| {v} | [{label}](datasets/{label}/summary.md) | {med([p['default'] for p in ps]):.3f} | {med([p['ceiling_128'] for p in ps]):.3f} | " +
                         ", ".join(ratio_text(p["ratio"]) for p in ps) + " | " +
                         ", ".join(ratio_text(p["ratio"]) for p in d["server_took_pair_ratios"][v]) + " |")
    lines += ["", "## Spread across repetitions (reference excluded)", "", "| Version | All paired ratios min / median / max | Ratio relative range | 1024 round-median relative range | 128 round-median relative range | Spread flag |", "|---|---|---:|---:|---:|---|"]
    for v, r in ranges.items():
        p = r["paired_ratio"]
        lines.append(f"| {v} | {p['min']:.3f} / {p['median']:.3f} / {p['max']:.3f} | {p['relative_range']:.1%} | {r['default']['relative_range']:.1%} | {r['ceiling_128']['relative_range']:.1%} | {'YES' if r['spread_flag'] else 'no'} |")
    lines += ["", "Relative range = (maximum − minimum) / median. Each setting's round value is the median of its two fresh-JVM cell summaries. Ratio spread includes both opposite-order pairs in every repetition.",
              "Flags (>15% paired-ratio range or >20% setting round-median range) are descriptive diagnostics, **not validity gates or confidence intervals**. Keep every qualified observation, including outliers. Few repetitions do not estimate a host population.",
              "", "## Block drift", "", "The following cells differ by more than 20% between their two client block medians. This does not identify the cause or invalidate the retained response/layout checks; it warns against assuming steady-state timing.", ""]
    drift = []
    for label, (_, chosen) in selected.items():
        for v, item in chosen.items():
            for i, cell in enumerate(item["data"]["cells"], 1):
                a, b = cell["block_medians"]
                if abs(b / a - 1) > .20:
                    drift.append({"dataset": label, "version": v, "cell": i, "ceiling": cell["ceiling"], "blocks_ms": [a, b]})
                    lines.append(f"- {label}, {v}, JVM {i}, ceiling {cell['ceiling']}: {a:.3f} → {b:.3f} ms ({b / a - 1:+.1%}).")
    if not drift:
        lines.append("- No cell exceeded this descriptive threshold; that is not proof of steady state.")
    lines += ["", "## Provenance", ""]
    for label, d in datasets.items():
        lines.append(f"- {label}: source `{d['source_sha']}`, run `{d['run_url']}`; [raw records](datasets/{label}/raw).")
    lines += ["", "[Paired ratios](ratios.svg) · [Absolute latency](latency.svg) · [Standalone HTML](report.html)", "",
              "Engine/image identities, parameters, query and oracle hashes agree across datasets. Each matrix is separately validated; source/run provenance may differ. Source equality, live responses, host isolation, warmup sufficiency and actual cleanup are not independently certified by this offline comparison. Per-dataset reports preserve the runner/reporter evidence distinction.", ""]
    summary = "\n".join(lines)
    ratios, latency = comparison_svg(datasets, reference_label), comparison_svg(datasets, reference_label, latency=True)
    (output / "ratios.svg").write_text(ratios)
    (output / "latency.svg").write_text(latency)
    (output / "summary.md").write_text(summary)
    (output / "comparison.json").write_text(json.dumps({"schema": 1, "valid": True, "reference": reference_label,
        "datasets": datasets, "repetition_spreads": ranges, "block_drift": drift}, indent=2) + "\n")
    (output / "report.html").write_text('<!doctype html><meta charset="utf-8"><title>Matrix repeatability</title><style>body{font-family:sans-serif;max-width:1240px;margin:auto}svg{width:100%}pre{white-space:pre-wrap}</style>' + ratios + latency + '<pre>' + esc(summary) + '</pre>')
    print(f"Comparison PASS: {len(repetitions)} repetitions; reference={reference_label or 'none'}; all observations retained.")
    return 0


def self_test():
    with tempfile.TemporaryDirectory(prefix="keyword-sort-report-") as td:
        root = Path(td)
        good, out = root / "good", root / "good-results"
        good.mkdir()
        for v in VERSIONS:
            (good / v).mkdir()
            (good / v / "result.json").write_text(json.dumps(fake_result(v, v in ("1.3.20", "2.11.1"))), encoding="utf-8")
        assert run(good, out) == 0 and (out / "matrix.svg").exists() and (out / "requests.svg").exists()
        missing = root / "missing"
        shutil.copytree(good, missing)
        (missing / "2.19.0" / "result.json").unlink()
        assert run(missing, root / "missing-results") != 0
        malformed = root / "malformed"
        shutil.copytree(good, malformed)
        bad = json.loads((malformed / "2.12.0" / "result.json").read_text())
        bad["cells"][0]["samples"] = [1.0]
        (malformed / "2.12.0" / "result.json").write_text(json.dumps(bad), encoding="utf-8")
        assert run(malformed, root / "malformed-results") != 0
    print("self-test: PASS (positive, missing-version, and malformed-sample fixtures used only in temporary directories; no repository results written)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="artifacts")
    parser.add_argument("--output", default="results")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--version", choices=VERSIONS,
                           help="report one version's pairs without a matrix verdict")
    selection.add_argument("--compare", nargs="+", metavar="LABEL=INPUT",
                           help="compare 2–6 complete five-version matrices without pooling requests")
    parser.add_argument("--reference", metavar="LABEL=INPUT",
                        help="optional separate comparison baseline, excluded from repetition spreads")
    selection.add_argument("--historical-matrix", action="store_true",
                           help="explicitly replay the original four-release evidence, without 3.8.0")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.reference and not args.compare:
        parser.error("--reference requires --compare")
    if args.compare:
        return compare_runs(args.compare, args.output, args.reference)
    return run(args.input, args.output, args.version, args.historical_matrix)


if __name__ == "__main__":
    raise SystemExit(main())
