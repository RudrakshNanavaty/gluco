"""Build Shields endpoint data from measured reports, never hardcoded percentages."""

import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    root, output = map(Path, sys.argv[1:3])
    output.mkdir(parents=True, exist_ok=True)
    components = []
    passed = failed = skipped = 0
    for name in ("backend", "frontend", "databricks"):
        folder = root / name
        filename = "coverage-summary.json" if name == "frontend" else "coverage.json"
        data = json.loads((folder / filename).read_text())
        if name == "frontend":
            lines = data["total"]["lines"]
            covered, total = lines["covered"], lines["total"]
        else:
            lines = data["totals"]
            covered, total = lines["covered_lines"], lines["num_statements"]
        if not 0 <= covered <= total or total <= 0:
            raise ValueError("Invalid measured coverage totals")
        percent = covered / total * 100
        components.append((name, covered, total, percent))
        tree = ET.parse(folder / "junit.xml").getroot()
        cases = list(tree.iter("testcase"))
        if not cases:
            raise ValueError("No test cases in report")
        for case in cases:
            if case.find("skipped") is not None:
                skipped += 1
            elif case.find("failure") is not None or case.find("error") is not None:
                failed += 1
            else:
                passed += 1
        endpoint = {
            "schemaVersion": 1,
            "label": f"{name} lines",
            "message": f"{percent:.1f}%",
            "color": "brightgreen"
            if percent >= 80
            else "yellow"
            if percent >= 50
            else "orange",
        }
        (output / f"{name}.json").write_text(json.dumps(endpoint) + "\n")
    (output / "tests.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "label": "unit tests",
                "message": f"{passed} passed · {failed} failed · {skipped} skipped",
                "color": "red" if failed else "brightgreen",
            }
        )
        + "\n"
    )
    repository, run = (
        os.environ.get("GITHUB_REPOSITORY", ""),
        os.environ.get("GITHUB_RUN_ID", ""),
    )
    link = (
        f"https://github.com/{repository}/actions/runs/{run}"
        if repository and run
        else "Local measurement"
    )
    summary = "# Measured unit-test line coverage\n\n| Component | Covered / executable lines | Coverage |\n|---|---:|---:|\n"
    for name, covered, total, percent in components:
        summary += f"| {name} | {covered} / {total} | {percent:.1f}% |\n"
    summary += f"\nTests: {passed} passed, {failed} failed, {skipped} skipped.\n\nEvidence: {link}\n\nCommit: {os.environ.get('GITHUB_SHA', 'local')}\n"
    summary += "\nSeparate denominators; no averaged project percentage. Databricks includes unexecuted cloud notebooks; live-database checks and model-accuracy metrics are separate.\n"
    (output / "README.md").write_text(summary)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as file:
            file.write(summary)
    print(summary)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
