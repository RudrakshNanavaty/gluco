"""Generate and verify a resolved dependency-license inventory.

Refresh mode reads both lockfiles and queries the official PyPI and npm registry
metadata APIs. Check mode is offline and fails when lockfiles change, packages
are missing, or license metadata is unresolved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tomllib
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UV_LOCK = ROOT / "back-end" / "uv.lock"
BUN_LOCK = ROOT / "front-end" / "bun.lock"
OUTPUT_JSON = ROOT / "docs" / "dependencies" / "licenses.json"
OUTPUT_MD = ROOT / "docs" / "dependencies" / "README.md"
USER_AGENT = "gluco-license-inventory/1.0"
BUN_PACKAGE = re.compile(r'^    "[^"]+": \["([^"]+@[^"/]+)"', re.MULTILINE)


@dataclass(frozen=True, order=True)
class Package:
    ecosystem: str
    name: str
    version: str


def digest(path: Path) -> str:
    # Git may check text files out as CRLF on Windows and LF in CI. Hash the
    # logical lockfile content so the same commit has one portable digest.
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def parse_python_packages(text: str) -> set[Package]:
    document = tomllib.loads(text)
    result: set[Package] = set()
    for package in document.get("package", []):
        source = package.get("source", {})
        if "registry" in source:
            result.add(Package("PyPI", package["name"], package["version"]))
    return result


def split_npm_spec(spec: str) -> tuple[str, str]:
    name, version = spec.rsplit("@", 1)
    return name, version


def parse_npm_packages(text: str) -> set[Package]:
    result: set[Package] = set()
    for match in BUN_PACKAGE.finditer(text):
        name, version = split_npm_spec(match.group(1))
        if version and not version.startswith(("workspace:", "link:", "file:")):
            result.add(Package("npm", name, version))
    return result


def normalized_license(value: object, classifiers: list[str] | None = None) -> str:
    if isinstance(value, dict):
        value = value.get("type") or value.get("name")
    if isinstance(value, list):
        value = " OR ".join(str(item) for item in value if item)
    if isinstance(value, str) and value.strip() and value.strip().upper() != "UNKNOWN":
        return " ".join(value.split())
    for classifier in classifiers or []:
        marker = "License :: OSI Approved :: "
        if classifier.startswith(marker):
            return classifier.removeprefix(marker)
    return "UNKNOWN"


def request_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def package_metadata(package: Package) -> dict[str, str]:
    if package.ecosystem == "PyPI":
        name = urllib.parse.quote(package.name, safe="")
        version = urllib.parse.quote(package.version, safe="")
        payload = request_json(f"https://pypi.org/pypi/{name}/{version}/json")
        info = payload.get("info", {})
        classifiers = info.get("classifiers", []) if isinstance(info, dict) else []
        license_value = None
        source = ""
        if isinstance(info, dict):
            license_value = info.get("license_expression") or info.get("license")
            urls = info.get("project_urls") or {}
            if isinstance(urls, dict):
                source = str(urls.get("Source") or urls.get("Repository") or urls.get("Homepage") or "")
            source = source or str(info.get("home_page") or info.get("package_url") or "")
        license_name = normalized_license(license_value, classifiers if isinstance(classifiers, list) else [])
    else:
        name = urllib.parse.quote(package.name, safe="")
        version = urllib.parse.quote(package.version, safe="")
        payload = request_json(f"https://registry.npmjs.org/{name}/{version}")
        license_name = normalized_license(payload.get("license"))
        repository = payload.get("repository")
        if isinstance(repository, dict):
            source = str(repository.get("url") or "")
        else:
            source = str(repository or payload.get("homepage") or "")
    return {
        **asdict(package),
        "license": license_name,
        "source": source.replace("git+", ""),
    }


def expected_packages() -> set[Package]:
    return parse_python_packages(UV_LOCK.read_text(encoding="utf-8")) | parse_npm_packages(
        BUN_LOCK.read_text(encoding="utf-8")
    )


def refresh() -> int:
    packages = sorted(expected_packages())
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(package_metadata, package): package for package in packages}
        for future in as_completed(futures):
            package = futures[future]
            try:
                rows.append(future.result())
            except Exception as error:  # network/registry errors are reported together
                errors.append(f"{package.ecosystem}:{package.name}@{package.version}: {error}")
    if errors:
        print("Registry metadata failures:\n" + "\n".join(sorted(errors)))
        return 1
    rows.sort(key=lambda row: (row["ecosystem"], row["name"].lower(), row["version"]))
    unresolved = [row for row in rows if row["license"] == "UNKNOWN"]
    document = {
        "schema": 1,
        "generated_from": {
            "back-end/uv.lock": digest(UV_LOCK),
            "front-end/bun.lock": digest(BUN_LOCK),
        },
        "package_count": len(rows),
        "unresolved_count": len(unresolved),
        "packages": rows,
    }
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["license"]] = counts.get(row["license"], 0) + 1
    lines = [
        "<!-- Generated by scripts/dependency_licenses.py --refresh; do not edit. -->",
        "",
        "# Resolved dependency licenses",
        "",
        f"This inventory covers **{len(rows)} resolved packages** from `back-end/uv.lock` and `front-end/bun.lock`.",
        "Registry metadata was retrieved from the official PyPI and npm APIs. The machine-readable evidence is in [`licenses.json`](licenses.json).",
        "",
        "## Summary",
        "",
        "| Reported license | Packages |",
        "|---|---:|",
    ]
    lines.extend(f"| {license_name.replace('|', '/')} | {count} |" for license_name, count in sorted(counts.items()))
    lines.extend(
        [
            "",
            "## Packages",
            "",
            "| Ecosystem | Package | Version | Reported license | Source |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        source = f"[upstream]({row['source']})" if row["source"].startswith(("http://", "https://")) else "registry metadata"
        lines.append(
            f"| {row['ecosystem']} | `{row['name']}` | `{row['version']}` | {row['license'].replace('|', '/')} | {source} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This report records package metadata; it is not legal advice. Distributed license and NOTICE files control when metadata differs. CI verifies lockfile coverage and fails when any package has unresolved license metadata.",
            "",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Recorded {len(rows)} packages; {len(unresolved)} unresolved licenses.")
    return 1 if unresolved else 0


def check() -> int:
    if not OUTPUT_JSON.exists() or not OUTPUT_MD.exists():
        print("Dependency-license inventory is missing. Run with --refresh.")
        return 1
    document = json.loads(OUTPUT_JSON.read_text(encoding="utf-8"))
    expected_hashes = {
        "back-end/uv.lock": digest(UV_LOCK),
        "front-end/bun.lock": digest(BUN_LOCK),
    }
    if document.get("generated_from") != expected_hashes:
        print("Dependency-license inventory is stale because a lockfile changed.")
        return 1
    expected = expected_packages()
    recorded = {
        Package(row["ecosystem"], row["name"], row["version"])
        for row in document.get("packages", [])
    }
    missing = sorted(expected - recorded)
    extra = sorted(recorded - expected)
    unresolved = [row for row in document.get("packages", []) if row.get("license") == "UNKNOWN"]
    if missing or extra or unresolved:
        print(f"Missing: {len(missing)}; extra: {len(extra)}; unresolved: {len(unresolved)}")
        return 1
    print(f"Verified {len(recorded)} resolved package licenses against both lockfiles.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="query registries and rewrite the inventory")
    args = parser.parse_args()
    return refresh() if args.refresh else check()


if __name__ == "__main__":
    raise SystemExit(main())
