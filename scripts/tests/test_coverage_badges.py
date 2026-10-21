"""Check measured denominators and failed/skipped test accounting."""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "coverage_badges", Path(__file__).parents[1] / "coverage_badges.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BadgeReports(unittest.TestCase):
    def run_reports(self, xml, covered=3, total=4):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for name in ("backend", "frontend", "databricks"):
            folder = root / name
            folder.mkdir()
            (folder / "junit.xml").write_text(xml)
            filename = (
                "coverage-summary.json" if name == "frontend" else "coverage.json"
            )
            data = (
                {"total": {"lines": {"covered": covered, "total": total}}}
                if name == "frontend"
                else {"totals": {"covered_lines": covered, "num_statements": total}}
            )
            (folder / filename).write_text(json.dumps(data))
        output = root / "output"
        with (
            patch.object(sys, "argv", ["coverage_badges.py", str(root), str(output)]),
            patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": ""}),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            module.main()
        return output

    def test_measured_percent_and_skips_are_not_passing_tests(self):
        output = self.run_reports(
            "<testsuites><testsuite><testcase/><testcase><skipped/></testcase></testsuite></testsuites>"
        )
        self.assertEqual(
            json.loads((output / "backend.json").read_text())["message"], "75.0%"
        )
        self.assertEqual(
            json.loads((output / "tests.json").read_text())["message"],
            "3 passed · 0 failed · 3 skipped",
        )

    def test_failed_tests_cannot_produce_successful_report(self):
        with self.assertRaises(SystemExit) as result:
            self.run_reports("<testsuite><testcase><failure/></testcase></testsuite>")
        self.assertEqual(result.exception.code, 1)

    def test_missing_cases_and_impossible_denominator_fail(self):
        with self.assertRaises(ValueError):
            self.run_reports("<testsuite/>")
        with self.assertRaises(ValueError):
            self.run_reports("<testsuite><testcase/></testsuite>", covered=5, total=4)


class QualityReports(unittest.TestCase):
    def test_only_actual_success_is_green(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            module.write_quality_badges(
                output,
                {
                    "ruff-lint": "success",
                    "ruff-format": "failure",
                    "python-types": "skipped",
                    "eslint": "cancelled",
                },
            )
            expected = {
                "ruff-lint": ("passing", "brightgreen"),
                "ruff-format": ("failure", "red"),
                "python-types": ("skipped", "lightgrey"),
                "eslint": ("cancelled", "lightgrey"),
                "typescript": ("unknown", "lightgrey"),
            }
            for name, (message, color) in expected.items():
                badge = json.loads((output / f"{name}.json").read_text())
                self.assertEqual((badge["message"], badge["color"]), (message, color))
            self.assertEqual(
                json.loads((output / "quality.json").read_text())["outcomes"][
                    "typescript"
                ],
                "unknown",
            )

    def test_empty_outcome_is_unknown_and_invalid_outcome_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            module.write_quality_badges(output, {"ruff-lint": ""})
            self.assertEqual(
                json.loads((output / "ruff-lint.json").read_text())["message"],
                "unknown",
            )
            with self.assertRaises(ValueError):
                module.write_quality_badges(output, {"ruff-lint": "looks good"})


if __name__ == "__main__":
    unittest.main()
