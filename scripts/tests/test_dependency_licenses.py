import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "dependency_licenses.py"
SPEC = importlib.util.spec_from_file_location("dependency_licenses", SCRIPT)
assert SPEC and SPEC.loader
LICENSES = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LICENSES
SPEC.loader.exec_module(LICENSES)


class DependencyLicenseTests(unittest.TestCase):
    def test_parses_scoped_and_plain_npm_packages(self) -> None:
        text = '''  "packages": {
    "react": ["react@19.2.8", "", {}],
    "@scope/tool": ["@scope/tool@2.1.0", "", {}],
  }'''
        packages = LICENSES.parse_npm_packages(text)
        self.assertIn(LICENSES.Package("npm", "react", "19.2.8"), packages)
        self.assertIn(LICENSES.Package("npm", "@scope/tool", "2.1.0"), packages)

    def test_parses_only_registry_python_packages(self) -> None:
        text = '''version = 1
[[package]]
name = "local"
version = "1.0.0"
source = { editable = "." }
[[package]]
name = "remote"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }
'''
        self.assertEqual(
            LICENSES.parse_python_packages(text),
            {LICENSES.Package("PyPI", "remote", "2.0.0")},
        )

    def test_license_normalization_uses_classifier_fallback(self) -> None:
        self.assertEqual(
            LICENSES.normalized_license("UNKNOWN", ["License :: OSI Approved :: MIT License"]),
            "MIT License",
        )


if __name__ == "__main__":
    unittest.main()
