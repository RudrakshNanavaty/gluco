import ast
import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "generate_reference_docs.py"
SPEC = importlib.util.spec_from_file_location("generate_reference_docs", SCRIPT)
assert SPEC and SPEC.loader
DOCS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DOCS
SPEC.loader.exec_module(DOCS)


class ReferenceGeneratorTests(unittest.TestCase):
    def test_docstring_summary_uses_first_paragraph(self) -> None:
        self.assertEqual(DOCS.summary("First line.\n\nDetails."), "First line.")

    def test_signature_includes_annotations_and_defaults(self) -> None:
        node = ast.parse("def example(value: int, limit: str = 'x') -> bool: ...").body[0]
        self.assertEqual(
            DOCS.python_signature(node),
            "example(value: int, limit: str = ...) -> bool",
        )

    def test_generated_documents_have_navigation_and_source_links(self) -> None:
        documents = DOCS.build_documents()
        index = documents[DOCS.OUTPUT / "README.md"]
        backend = documents[DOCS.OUTPUT / "back-end.md"]
        self.assertIn("HTTP API", index)
        self.assertIn("View source", backend)
        self.assertTrue(all(text.startswith(DOCS.GENERATED_NOTICE) for text in documents.values()))


if __name__ == "__main__":
    unittest.main()
