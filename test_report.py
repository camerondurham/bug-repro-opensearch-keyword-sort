"""Offline replay of committed evidence; no Docker, HTTP, or new measurements."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import statistics
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import report

ROOT = Path(__file__).resolve().parent
# Compare raw replay with its committed numerical snapshot, including after a new run.
PUBLISHED = json.loads((ROOT / "results/metrics.json").read_text())


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Fail if offline replay accidentally tries an external command or HTTP.
        for target in ("subprocess.run", "urllib.request.urlopen"):
            patcher = patch(target, side_effect=AssertionError("offline replay attempted external I/O"))
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = report.main(list(args))
        return code, stdout.getvalue()

    def test_committed_raw_replay_and_in_place_regeneration(self):
        output = self.root / "results"
        raw = output / "raw"
        shutil.copytree(ROOT / "results/raw", raw)
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.glob("*.json")}
        selection = ["--historical-matrix"] if PUBLISHED["versions"] == list(report.HISTORICAL_VERSIONS) else []
        for input_path in (raw, output):
            code, _ = self.run_cli("--input", str(input_path), "--output", str(output), *selection)
            self.assertEqual(code, 0)
            metrics = json.loads((output / "metrics.json").read_text())
            self.assertEqual(metrics["outcome"], PUBLISHED["outcome"])
            self.assertEqual(metrics["pair_ratios"], PUBLISHED["pair_ratios"])
            for version in PUBLISHED["versions"]:
                record = json.loads((raw / f"{version}.json").read_text())
                # Independently recompute server cell medians from original arrays.
                cell_took = [statistics.median([statistics.median(c["took_ms"][:100]),
                                               statistics.median(c["took_ms"][100:])])
                             for c in record["cells"]]
                for pair, (a, b) in zip(metrics["server_took_pair_ratios"][version], ((0, 1), (3, 2))):
                    self.assertEqual(pair, {"default": cell_took[a], "ceiling_128": cell_took[b],
                                            "ratio": cell_took[a] / cell_took[b]})
            matrix = (output / "matrix.svg").read_text()
            requests = (output / "requests.svg").read_text()
            self.assertIn("Keyword-sort latency by clause limit", matrix)
            self.assertIn("Default limit: 1024", matrix)
            self.assertIn("Lowered limit: 128", matrix)
            self.assertNotIn("fresh JVM", matrix)
            self.assertNotIn("fresh-JVM", matrix)
            self.assertIn("Container 1 (1024)", requests)
            self.assertNotIn("fresh JVM", requests)
            self.assertNotIn("fresh-JVM", requests)
            points = ET.parse(output / "requests.svg").findall(".//{http://www.w3.org/2000/svg}circle")
            self.assertEqual(len(points), 800 * len(PUBLISHED["versions"]))
            summary = (output / "summary.md").read_text()
            self.assertIn("Default limit 1024 (ms)", summary)
            self.assertIn("Lowered limit 128 (ms)", summary)
            self.assertIn("Server `took`", summary)
            self.assertIn("cannot independently replay the response oracle", summary)
            self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in raw.glob("*.json")})

    def test_single_version_prints_pairs_without_matrix_verdict(self):
        source = ROOT / "results/raw/2.19.0.json"
        output = self.root / "single"
        code, text = self.run_cli("--input", str(source), "--output", str(output), "--version", "2.19.0")
        self.assertEqual(code, 0)
        for n, pair in enumerate(PUBLISHED["pair_ratios"]["2.19.0"], 1):
            self.assertIn(f"pair {n}: client {pair['ratio']:.3f}×", text)
        self.assertIn("server took", text)
        self.assertNotIn("REPRODUCED", text)
        metrics = json.loads((output / "metrics.json").read_text())
        self.assertEqual(metrics["outcome"], "NOT_ASSESSED")
        self.assertEqual(metrics["versions"], ["2.19.0"])
        # Default full-matrix reporting still rejects an incomplete Actions download.
        self.assertEqual(self.run_cli("--input", str(source), "--output", str(output))[0], 1)

    def test_latest_release_is_required_but_not_presumed_affected(self):
        import repro
        self.assertEqual(tuple(repro.VERSIONS), report.VERSIONS)
        self.assertEqual(set(repro.IMAGE_DIGESTS), set(report.VERSIONS))
        self.assertEqual(repro.VERSIONS["3.8.0"], "10.5.0")
        self.assertNotIn("3.0.0", report.VERSIONS)
        workflow = (ROOT / ".github/workflows/reproduce.yml").read_text()
        self.assertIn("version: " + repr(list(report.VERSIONS)), workflow)
        inputs = self.root / "inputs"
        for version in report.VERSIONS:
            path = inputs / version / "result.json"
            path.parent.mkdir(parents=True)
            # A null latest-release effect must not change the historical-boundary verdict.
            record = report.fake_result(version, controls=version in ("1.3.20", "2.11.1", "3.8.0"))
            path.write_text(json.dumps(record))
        output = self.root / "matrix"
        self.assertEqual(self.run_cli("--input", str(inputs), "--output", str(output))[0], 0)
        metrics = json.loads((output / "metrics.json").read_text())
        self.assertEqual(metrics["versions"], list(report.VERSIONS))
        self.assertEqual(metrics["outcome"], "REPRODUCED")
        self.assertEqual(metrics["outcome_scope"], "historical_1.x_2.x_boundary")
        self.assertEqual(len(ET.parse(output / "requests.svg").findall(".//{http://www.w3.org/2000/svg}circle")), 4000)
        code, text = self.run_cli("--input", str(inputs), "--output", str(output), "--version", "3.8.0")
        self.assertEqual(code, 0)
        self.assertIn("NOT_ASSESSED", text)
        (inputs / "3.8.0/result.json").unlink()
        self.assertEqual(self.run_cli("--input", str(inputs), "--output", str(output))[0], 1)
        self.assertEqual(self.run_cli("--input", str(inputs), "--output", str(output), "--historical-matrix")[0], 0)

    def comparison_fixture(self, label, factor=1):
        root = self.root / label
        for version in report.VERSIONS:
            d = report.fake_result(version)
            d["source_sha"] = "source-" + label
            for cell in d["cells"]:
                cell["identity"]["image"].update(Id="fake-image-" + version, pinned_reference="fake-pin-" + version)
                if cell["ceiling"] == 1024:
                    cell["samples"] = [x * factor for x in cell["samples"]]
                    cell["block_medians"] = [x * factor for x in cell["block_medians"]]
            path = root / version / "result.json"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps(d))
        return root

    def test_comparison_keeps_reference_and_raw_matrices_separate(self):
        a, b, baseline = (self.comparison_fixture("a"), self.comparison_fixture("b", 1.1),
                          self.comparison_fixture("baseline", 5))
        output = self.root / "comparison"
        code, _ = self.run_cli("--compare", f"a={a}", f"b={b}", "--reference", f"hosted={baseline}", "--output", str(output))
        self.assertEqual(code, 0)
        d = json.loads((output / "comparison.json").read_text())
        self.assertTrue(d["valid"])
        self.assertEqual(d["reference"], "hosted")
        self.assertAlmostEqual(d["repetition_spreads"]["2.12.0"]["paired_ratio"]["max"], 1.65)
        self.assertEqual(len(ET.parse(output / "ratios.svg").findall(".//{http://www.w3.org/2000/svg}circle")), 30)
        self.assertEqual((output / "datasets/a/raw/3.8.0.json").read_bytes(), (a / "3.8.0/result.json").read_bytes())
        self.assertIn("not validity gates", (output / "summary.md").read_text())

    def test_comparison_rejects_duplicate_missing_and_mismatched_evidence(self):
        a, b = self.comparison_fixture("a"), self.comparison_fixture("b")
        output = self.root / "comparison"
        self.assertEqual(self.run_cli("--compare", f"a={a}", f"b={a}", "--output", str(output))[0], 1)
        self.assertEqual(self.run_cli("--compare", f"a={a}", f"b={b}", "--output", str(output))[0], 0)
        path = b / "3.8.0/result.json"
        d = json.loads(path.read_text())
        d["cells"][0]["identity"]["image"]["Id"] = "different-image"
        path.write_text(json.dumps(d))
        self.assertEqual(self.run_cli("--compare", f"a={a}", f"b={b}", "--output", str(output))[0], 1)
        self.assertIn("INVALID", (output / "report.html").read_text())
        self.assertIn("INVALID", (output / "ratios.svg").read_text())
        path.unlink()
        self.assertEqual(self.run_cli("--compare", f"a={a}", f"b={b}", "--output", str(output))[0], 1)

    def test_nondefault_runner_parameters_and_zero_took(self):
        record = report.fake_result("2.19.0")
        record["parameters"].update(docs=1000, shards=1, heap="1g", samples=30,
                                    block_warmups=0, chunk=100, max_seconds=120)
        for cell in record["cells"]:
            cell["samples"] = cell["samples"][:30] + cell["samples"][100:130]
            cell["took_ms"] = [0] * 60
        source = self.root / "result.json"
        source.write_text(json.dumps(record))
        output = self.root / "custom"
        code, text = self.run_cli("--input", str(source), "--output", str(output), "--version", "2.19.0")
        self.assertEqual(code, 0)
        self.assertIn("n/a (zero denominator)", text)
        graph = (output / "requests.svg").read_text()
        self.assertIn("N=240", graph)
        self.assertNotIn("100-sample", graph)
        self.assertEqual(len(ET.fromstring(graph).findall(".//{http://www.w3.org/2000/svg}circle")), 240)
        self.assertIn('"heap": "1g"', (output / "summary.md").read_text())
        bad = copy.deepcopy(record)
        bad["cells"][0]["block_medians"][0] += 1
        self.assertTrue(any("do not match samples" in e for e in report.validate_record({"data": bad})))
        bad = copy.deepcopy(record)
        bad["parameters"]["samples"] = 31
        self.assertTrue(any("count does not match" in e for e in report.validate_record({"data": bad})))


if __name__ == "__main__":
    unittest.main()
