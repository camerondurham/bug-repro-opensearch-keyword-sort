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
# Fixed expected ratios from measured source 4ad6043 / publication 3d8ed06.
PUBLISHED_RATIOS = {
    "1.3.20": [1.0034943171811455, 1.0293235019424254],
    "2.11.1": [1.0216281939049545, 0.9546688764085531],
    "2.12.0": [2.745573952499589, 2.7451876722384116],
    "2.19.0": [2.654150825693497, 2.3628116185487156],
}


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
        for input_path in (raw, output):
            code, _ = self.run_cli("--input", str(input_path), "--output", str(output))
            self.assertEqual(code, 0)
            metrics = json.loads((output / "metrics.json").read_text())
            self.assertEqual(metrics["outcome"], "REPRODUCED")
            for version, expected in PUBLISHED_RATIOS.items():
                self.assertEqual([p["ratio"] for p in metrics["pair_ratios"][version]], expected)
                record = json.loads((raw / f"{version}.json").read_text())
                # Independently recompute server cell medians from original arrays.
                cell_took = [statistics.median([statistics.median(c["took_ms"][:100]),
                                               statistics.median(c["took_ms"][100:])])
                             for c in record["cells"]]
                for pair, (a, b) in zip(metrics["server_took_pair_ratios"][version], ((0, 1), (3, 2))):
                    self.assertEqual(pair, {"default": cell_took[a], "ceiling_128": cell_took[b],
                                            "ratio": cell_took[a] / cell_took[b]})
            points = ET.parse(output / "requests.svg").findall(".//{http://www.w3.org/2000/svg}circle")
            self.assertEqual(len(points), 3200)
            summary = (output / "summary.md").read_text()
            self.assertIn("Server `took`", summary)
            self.assertIn("cannot independently replay the response oracle", summary)
            self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in raw.glob("*.json")})

    def test_single_version_prints_pairs_without_matrix_verdict(self):
        source = ROOT / "results/raw/2.19.0.json"
        output = self.root / "single"
        code, text = self.run_cli("--input", str(source), "--output", str(output), "--version", "2.19.0")
        self.assertEqual(code, 0)
        self.assertIn("pair 1: client 2.654×", text)
        self.assertIn("pair 2: client 2.363×", text)
        self.assertIn("server took", text)
        self.assertNotIn("REPRODUCED", text)
        metrics = json.loads((output / "metrics.json").read_text())
        self.assertEqual(metrics["outcome"], "NOT_ASSESSED")
        self.assertEqual(metrics["versions"], ["2.19.0"])
        # Default full-matrix reporting still rejects an incomplete Actions download.
        self.assertEqual(self.run_cli("--input", str(source), "--output", str(output))[0], 1)

    def test_exploratory_3x_is_supported_without_changing_matrix_verdict(self):
        import repro
        self.assertEqual(set(report.SUPPORTED_VERSIONS), set(repro.VERSIONS))
        self.assertEqual(set(repro.IMAGE_DIGESTS), set(repro.VERSIONS))
        self.assertEqual(repro.VERSIONS["3.0.0"], "10.1.0")
        source = self.root / "result.json"
        source.write_text(json.dumps(report.fake_result("3.0.0")))
        output = self.root / "trial"
        code, text = self.run_cli("--input", str(source), "--output", str(output), "--version", "3.0.0")
        self.assertEqual(code, 0)
        self.assertIn("NOT_ASSESSED", text)
        self.assertNotIn("REPRODUCED", text)
        metrics = json.loads((output / "metrics.json").read_text())
        self.assertEqual(metrics["versions"], ["3.0.0"])
        self.assertEqual(len(metrics["pair_ratios"]["3.0.0"]), 2)
        self.assertEqual(report.VERSIONS, ("1.3.20", "2.11.1", "2.12.0", "2.19.0"))

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
