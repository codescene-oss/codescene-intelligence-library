"""Tests for build_release.py: the zip ships only what clients need, as committed, and builds reproducibly.

    python -m unittest discover scripts
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

import build_release

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "valid"


class BuildReleaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.root)
        (self.root / "LICENSE").write_text("License text\n")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "guide.md").write_text("# Not shipped\n")
        self.git("init", "-q")
        self.commit()
        self.out = Path(self.tmp.name) / "dist"

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def commit(self):
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "build")

    def build(self, **kwargs):
        return build_release.build(self.root, self.out, **kwargs)

    def test_ships_only_client_files_with_a_manifest(self):
        with zipfile.ZipFile(self.build()) as archive:
            names = archive.namelist()
            manifest = json.loads(archive.read("MANIFEST.json"))
            for name in names:
                if name != "MANIFEST.json":
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), manifest["files"][name])
        self.assertIn("catalog.json", names)
        self.assertIn("LICENSE", names)
        self.assertIn("skills/demo/SKILL.md", names)
        self.assertNotIn("docs/guide.md", names)
        self.assertEqual(sorted(set(names) - {"MANIFEST.json"}), sorted(manifest["files"]))
        self.assertEqual("1.0.0", manifest["version"])

    def test_names_the_zip_and_checksum_after_the_version(self):
        zip_path = self.build()
        self.assertEqual("codescene-intelligence-library-1.0.0.zip", zip_path.name)
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        self.assertEqual(f"{digest}  {zip_path.name}\n", Path(f"{zip_path}.sha256").read_text())

    def test_reproducible(self):
        first = self.build().read_bytes()
        self.assertEqual(first, self.build().read_bytes())

    def test_uses_the_commit_not_the_working_tree(self):
        (self.root / "skills" / "demo" / "SKILL.md").write_text("Uncommitted edit\n")
        (self.root / "skills" / "demo" / "untracked.md").write_text("Untracked\n")
        with zipfile.ZipFile(self.build()) as archive:
            self.assertNotIn(b"Uncommitted", archive.read("skills/demo/SKILL.md"))
            self.assertNotIn("skills/demo/untracked.md", archive.namelist())

    def test_tag_must_match_the_catalog_version(self):
        self.build(tag="v1.0.0")
        with self.assertRaises(ValueError):
            self.build(tag="v1.0.1")


if __name__ == "__main__":
    unittest.main()
