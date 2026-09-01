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

    def base_files(self):
        return {
            "SUMMARY.md": "# Summary\n\n- [One](src/one.md)\n- [Two](src/two.md#part)\n",
            "src/one.md": "# One\n\nA [link](https://example.test/a) and ![diagram](assets/a.bin).\n\n```rust\nfn main() {}\n```\n",
            "src/two.md": "# Two\n\nSee [ref][r].\n\n[r]: https://example.test/ref\n\n~~~text\ncompiler output\n~~~\n",
            "src/assets/a.bin": b"asset bytes",
        }

    def test_prose_only_changes_pass(self):
        source = self.base_files()
        target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("# One", "# Un").replace("A ", "Une ")
        self.assertEqual(self.run_validator(source, target).returncode, 0)

    def test_rust_fence_change_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("fn main() {}", "fn main() { println!(\"x\"); }")
        self.assertNotEqual(self.run_validator(source, target).returncode, 0)

    def test_text_fence_change_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/two.md"] = target["src/two.md"].replace("compiler output", "changed output")
        self.assertNotEqual(self.run_validator(source, target).returncode, 0)

    def test_missing_page_fails(self):
        source = self.base_files(); target = dict(source); del target["src/two.md"]
        self.assertNotEqual(self.run_validator(source, target).returncode, 0)

    def test_changed_url_fails(self):
        source = self.base_files(); target = dict(source)
        target["src/one.md"] = target["src/one.md"].replace("https://example.test/a", "https://other.test/a")
        self.assertNotEqual(self.run_validator(source, target).returncode, 0)

    def test_changed_image_bytes_fails(self):
        source = self.base_files(); target = dict(source); target["src/assets/a.bin"] = b"other bytes"
        self.assertNotEqual(self.run_validator(source, target).returncode, 0)

    def test_changed_summary_destination_fails(self):
        source = self.base_files(); target = dict(source)
        target["SUMMARY.md"] = target["SUMMARY.md"].replace("src/two.md#part", "src/one.md")
        self.assertNotEqual(self.run_validator(source, target).returncode, 0)


if __name__ == "__main__":
    unittest.main()
