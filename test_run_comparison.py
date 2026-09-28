import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import run_comparison as runner


class ComparisonRunnerTests(unittest.TestCase):
    def fake_command(self, calls, fail=None):
        def command(argv, env):
            calls.append((list(argv), dict(env)))
            if fail and fail(argv):
                raise RuntimeError("synthetic child failure")
            destination = Path(argv[argv.index("--output") + 1])
            destination.mkdir(parents=True, exist_ok=True)
            if str(runner.REPORT) in argv:
                (destination / "report.html").write_text("NOT_REPRODUCED", encoding="utf-8")
            else:
                (destination / "result.json").write_text("{}\n", encoding="utf-8")
        return command

    def owned_output(self, path):
        path.mkdir()
        (path / "host.json").write_text(json.dumps({"generator": runner.GENERATOR}), encoding="utf-8")
        (path / "sentinel").write_text("old", encoding="utf-8")

    def test_runs_exact_matrix_and_publishes_without_effect_gate(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "comparison"
            calls = []
            with mock.patch.object(runner, "git_snapshot", side_effect=["sha", "sha"]), \
                    mock.patch.object(runner, "run_command", side_effect=self.fake_command(calls)), \
                    mock.patch.object(runner, "host_details", return_value={"cpu_count": 1}):
                self.assertEqual(runner.run(output), 0)
            measurements = [call for call, _ in calls if str(runner.REPRO) in call]
            reports = [call for call, _ in calls if str(runner.REPORT) in call]
            self.assertEqual(len(measurements), 15)
            self.assertEqual(len(reports), 1)
            self.assertEqual([call[call.index("--version") + 1] for call in measurements],
                             [v for order in runner.ORDERS for v in order])
            self.assertTrue(all(call[call.index("--max-seconds") + 1] == "780" for call in measurements))
            self.assertEqual(reports[0][reports[0].index("--compare") + 1:reports[0].index("--reference")],
                             [x for x in reports[0] if x.startswith("local-")])
            for _, env in calls:
                self.assertEqual(env["GITHUB_SHA"], "sha")
                self.assertNotIn("GITHUB_RUN_ID", env)
                self.assertNotIn("GITHUB_REPOSITORY", env)
            self.assertTrue((output / "report.html").exists())
            self.assertEqual(json.loads((output / "host.json").read_text())["source_sha"], "sha")
            self.assertFalse(list(output.parent.glob(f".{output.name}.staging-*")))

    def test_existing_output_refuses_then_owned_replace_succeeds(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "comparison"
            self.owned_output(output)
            calls = []
            with mock.patch.object(runner, "git_snapshot", return_value="sha"), \
                    mock.patch.object(runner, "run_command", side_effect=self.fake_command(calls)):
                self.assertNotEqual(runner.run(output), 0)
            self.assertEqual(calls, [])
            with mock.patch.object(runner, "git_snapshot", side_effect=["sha", "sha"]), \
                    mock.patch.object(runner, "run_command", side_effect=self.fake_command(calls)), \
                    mock.patch.object(runner, "host_details", return_value={}):
                self.assertEqual(runner.run(output, replace=True), 0)
            self.assertFalse((output / "sentinel").exists())
            self.assertTrue((output / "report.html").exists())
            self.assertEqual(len([c for c, _ in calls if str(runner.REPRO) in c]), 15)

    def test_failures_keep_previous_destination_and_staging(self):
        for failure in ("child", "report", "source"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as td:
                output = Path(td) / "comparison"
                self.owned_output(output)
                calls = []
                if failure == "child":
                    child_failure = lambda argv: str(runner.REPRO) in argv
                    snapshots = ["sha"]
                elif failure == "report":
                    child_failure = lambda argv: str(runner.REPORT) in argv
                    snapshots = ["sha"]
                else:
                    child_failure = None
                    snapshots = ["sha", "changed"]
                with mock.patch.object(runner, "git_snapshot", side_effect=snapshots), \
                        mock.patch.object(runner, "run_command", side_effect=self.fake_command(calls, child_failure)):
                    self.assertNotEqual(runner.run(output, replace=True), 0)
                self.assertEqual((output / "sentinel").read_text(), "old")
                self.assertFalse((output / "report.html").exists())
                self.assertTrue(list(output.parent.glob(f".{output.name}.staging-*")))

    def test_unsafe_unowned_and_symlink_destinations_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            unowned = base / "unowned"
            unowned.mkdir()
            target = base / "target"
            target.mkdir()
            link = base / "link"
            link.symlink_to(target, target_is_directory=True)
            with mock.patch.object(runner, "git_snapshot", return_value="sha"), \
                    mock.patch.object(runner, "run_command") as command:
                self.assertNotEqual(runner.run(unowned, replace=True), 0)
                self.assertNotEqual(runner.run(link, replace=True), 0)
                self.assertNotEqual(runner.run(runner.REFERENCE), 0)
                command.assert_not_called()

    def test_host_details_prefers_model_name_over_processor_index(self):
        fixtures = {
            "/proc/cpuinfo": "processor: 0\nmodel name: AMD Ryzen 7 7800X3D\nhardware: fallback\n",
            "/proc/meminfo": "MemTotal:       1234 kB\n",
        }

        def read_fixture(path, encoding="utf-8"):
            return fixtures[str(path)]

        with mock.patch.object(runner.Path, "read_text", new=read_fixture):
            details = runner.host_details()
        self.assertEqual(details["cpu_model"], "AMD Ryzen 7 7800X3D")
        self.assertEqual(details["ram_bytes"], 1234 * 1024)

    def test_postpublication_cleanup_failure_is_nonfatal(self):
        for replace in (False, True):
            with self.subTest(replace=replace), tempfile.TemporaryDirectory() as td:
                output = Path(td) / "comparison"
                if replace:
                    self.owned_output(output)
                calls, stderr = [], io.StringIO()
                with mock.patch.object(runner, "git_snapshot", side_effect=["sha", "sha"]), \
                        mock.patch.object(runner, "run_command", side_effect=self.fake_command(calls)), \
                        mock.patch.object(runner, "host_details", return_value={}), \
                        mock.patch.object(runner.shutil, "rmtree", side_effect=OSError("cleanup")), \
                        contextlib.redirect_stderr(stderr):
                    self.assertEqual(runner.run(output, replace=replace), 0)
                self.assertTrue((output / "report.html").exists())
                staging = list(output.parent.glob(f".{output.name}.staging-*"))
                self.assertEqual(len(staging), 1)
                self.assertIn(str(staging[0]), stderr.getvalue())

    def test_publish_failure_rolls_back_previous_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output, staging = root / "output", root / "staging"
            self.owned_output(output)
            report = staging / "report"
            report.mkdir(parents=True)
            (report / "report.html").write_text("new", encoding="utf-8")
            original = os.rename
            calls = []

            def rename(source, destination):
                calls.append((source, destination))
                if len(calls) == 2:
                    raise OSError("synthetic publish failure")
                return original(source, destination)

            with self.assertRaises(OSError), mock.patch.object(runner.os, "rename", side_effect=rename):
                runner.publish(staging, output, True, os.stat(output, follow_symlinks=False))
            self.assertEqual((output / "sentinel").read_text(), "old")
            self.assertTrue((staging / "report" / "report.html").exists())
            self.assertFalse((staging / "previous").exists())


if __name__ == "__main__":
    unittest.main()
