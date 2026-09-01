import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "verify_translation.py"


class VerifyTranslationTests(unittest.TestCase):
    def run_validator(self, source_files, target_files):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            for base, files in ((source, source_files), (target, target_files)):
                for name, content in files.items():
                    path = base / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if isinstance(content, bytes):
                        path.write_bytes(content)
                    else:
                        path.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(source), str(target)],
                capture_output=True, text=True, check=False,
            )

    def assert_failure(self, source, target, diagnostic):
        result = self.run_validator(source, target)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(diagnostic, result.stderr)

    def base_files(self):
        return {
            "src/SUMMARY.md": "# Summary\n\n- [One](one.md)\n- [Two](two.md#part)\n",
            "src/one.md": "# One\n\nA [link](https://example.test/a) and ![diagram](assets/a.bin).\n\n```rust\nfn main() {}\n```\n",
            "src/two.md": "# Two\n\nSee [ref][r].\n\n[r]: https://example.test/ref\n\n~~~text\ncompiler output\n~~~\n",
            "src/assets/a.bin": b"asset bytes",
            "lists/src/lib.rs": b"pub fn copied() {}\n",
            "src/assets/a.gif": b"GIF89a copied",
            "src/three.md": "# Three\n\n## Parts\n\n* alpha\n* beta\n\n> quoted note\n> continued\n",
            "book.toml": "[book]\ntitle = \"source\"\n",
        }

    def test_prose_only_changes_pass(self):
        source = self.base_files()
        target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("# One", "# Un").replace("A ", "Une ")
        self.assertEqual(self.run_validator(source, target).returncode, 0)

    def test_rust_fence_change_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("fn main() {}", "fn main() { println!(\"x\"); }")
        self.assert_failure(source, target, "fenced blocks differ")

    def test_text_fence_change_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/two.md"] = target["src/two.md"].replace("compiler output", "changed output")
        self.assert_failure(source, target, "fenced blocks differ")

    def test_missing_page_fails(self):
        source = self.base_files(); target = dict(source); del target["src/two.md"]
        self.assert_failure(source, target, "Markdown paths differ")

    def test_changed_url_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("https://example.test/a", "https://other.test/a")
        self.assert_failure(source, target, "protected link or image destinations differ")

    def test_changed_image_bytes_fails(self):
        source = self.base_files(); target = dict(source); target["src/assets/a.bin"] = b"other bytes"
        self.assert_failure(source, target, "Asset SHA-256 differs")

    def test_changed_summary_destination_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/SUMMARY.md"] = target["src/SUMMARY.md"].replace("two.md#part", "one.md")
        self.assert_failure(source, target, "SUMMARY.md: local destinations differ")

    def test_changed_reference_destination_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/two.md"] = target["src/two.md"].replace("https://example.test/ref", "https://other.test/ref")
        self.assert_failure(source, target, "protected link or image destinations differ")

    def test_changed_image_destination_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("assets/a.bin", "assets/missing.bin")
        self.assert_failure(source, target, "protected link or image destinations differ")

    def test_missing_asset_fails(self):
        source = self.base_files(); target = dict(source); del target["src/assets/a.bin"]
        self.assert_failure(source, target, "Missing copied asset")

    def test_fence_opening_changes_fail(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("```rust", "  ```python")
        self.assert_failure(source, target, "fenced blocks differ")

    def test_fence_closing_whitespace_changes_fail(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("```\n", "```  \n")
        self.assert_failure(source, target, "fenced blocks differ")

    def test_quoted_fence_body_changes_fail(self):
        source = self.base_files(); target = dict(source)
        source["src/one.md"] = "> ```text\n> quoted\n> ```\n"
        target["src/one.md"] = "> ```text\n> changed\n> ```\n"
        self.assert_failure(source, target, "fenced blocks differ")

    def test_visible_labels_and_alt_text_changes_pass(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("[link]", "[lien]").replace("![diagram]", "![schema]")
        self.assertEqual(self.run_validator(source, target).returncode, 0)

    def test_four_space_indented_code_changes_pass(self):
        source = self.base_files(); target = dict(source)
        source["src/one.md"] += "\n    ```text\n    indented\n    ```\n"
        target["src/one.md"] += "\n    ```text\n    changed\n    ```\n"
        self.assertEqual(self.run_validator(source, target).returncode, 0)

    def test_target_only_root_editorial_markdown_and_translated_metadata_pass(self):
        source = self.base_files(); target = dict(source)
        target["ATTRIBUTION.md"] = "# Attribution\n"
        target["TRANSLATION_GLOSSARY.md"] = "# Glossary\n"
        target["book.toml"] = "[book]\ntitle = \"translated\"\n"
        self.assertEqual(self.run_validator(source, target).returncode, 0)

    def test_missing_book_toml_fails_with_clear_diagnostic(self):
        source = self.base_files(); target = dict(source)
        del target["book.toml"]
        self.assert_failure(source, target, "Missing target book.toml")

    def test_changed_rust_asset_fails(self):
        source = self.base_files(); target = dict(source)
        target["lists/src/lib.rs"] = b"pub fn changed() {}\n"
        self.assert_failure(source, target, "Asset SHA-256 differs")

    def test_changed_gif_asset_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/assets/a.gif"] = b"GIF89a changed"
        self.assert_failure(source, target, "Asset SHA-256 differs")

    def test_translated_block_structure_passes(self):
        source = self.base_files(); target = dict(source)
        target["src/three.md"] = (
            "# \u4e09\n\n## \u90e8\u5206\n\n* \u7532\n* \u4e59\n\n> \u5f15\u7528\n> \u7eed\u884c\n"
        )
        self.assertEqual(self.run_validator(source, target).returncode, 0)

    def test_rewrapped_blockquote_passes(self):
        source = self.base_files(); target = dict(source)
        target["src/three.md"] = target["src/three.md"].replace(
            "> quoted note\n> continued\n", "> \u5f15\u7528\u5df2\u5408\u5e76\u4e3a\u4e00\u884c\n"
        )
        self.assertEqual(self.run_validator(source, target).returncode, 0)

    def test_dropped_heading_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/three.md"] = target["src/three.md"].replace("# Three", "Three", 1)
        self.assert_failure(source, target, "block structure differs")

    def test_changed_heading_level_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/three.md"] = target["src/three.md"].replace("## Parts", "### Parts", 1)
        self.assert_failure(source, target, "block structure differs")

    def test_dropped_list_marker_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/three.md"] = target["src/three.md"].replace("* beta", "beta", 1)
        self.assert_failure(source, target, "block structure differs")

    def test_dropped_blockquote_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/three.md"] = target["src/three.md"].replace(
            "> quoted note\n> continued\n", "quoted note continued\n"
        )
        self.assert_failure(source, target, "block structure differs")

    def test_block_structure_ignores_fenced_content(self):
        source = self.base_files(); target = dict(source)
        target["src/three.md"] = target["src/three.md"].replace(
            "# Three", "# \u4e09", 1
        ) + "\n```text\n# not a heading\n* not a list\n> not a quote\n```\n"
        source["src/three.md"] = source["src/three.md"] + "\n```text\n# not a heading\n* not a list\n> not a quote\n```\n"
        self.assertEqual(self.run_validator(source, target).returncode, 0)


if __name__ == "__main__":
    unittest.main()
