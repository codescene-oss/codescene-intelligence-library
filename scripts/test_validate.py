"""Tests for validate.py: a valid fixture skill passes, and each rule fails when broken.

    python -m unittest discover scripts
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import validate

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "valid"


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(FIXTURE, self.root)
        self.skill = self.root / "skills" / "demo"

    def tearDown(self):
        self.tmp.cleanup()

    def run_checks(self, **kwargs):
        return validate.validate(self.root, **kwargs)

    def assert_fails(self, rule, **kwargs):
        report = self.run_checks(**kwargs)
        self.assertIn(rule, report.rules_failed(), report.failures)
        return report

    def edit_json(self, path, change):
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data, indent=2) + "\n")

    def append(self, path, text):
        path.write_text(path.read_text() + text)

    def test_valid_fixture_passes(self):
        report = self.run_checks()
        self.assertEqual([], report.failures)
        self.assertEqual([], report.warnings)

    # --- Integrity checks ---

    def test_layout_missing_dir(self):
        shutil.rmtree(self.skill / "examples")
        self.assert_fails("layout")

    def test_folder_id(self):
        self.skill.rename(self.skill.with_name("other"))
        self.assert_fails("folder id")

    def test_skill_json_schema(self):
        self.edit_json(self.skill / "skill.json", lambda d: d.update(version="1.0"))
        self.assert_fails("skill.json schema")

    def test_invalid_json(self):
        (self.skill / "skill.json").write_text("{ not json")
        self.assert_fails("json")

    def test_min_server_version_required(self):
        self.edit_json(self.skill / "skill.json", lambda d: d.pop("min_server_version"))
        self.assert_fails("skill.json schema")

    def test_input_needs_description_and_type(self):
        for field in ["description", "type"]:
            with self.subTest(field=field):
                self.edit_json(self.skill / "skill.json", lambda d: d["inputs"][0].pop(field))
                self.assert_fails("skill.json schema")
                shutil.copy(FIXTURE / "skills" / "demo" / "skill.json", self.skill / "skill.json")

    def test_structured_input_needs_its_shape(self):
        for spec in [{"type": "object"}, {"type": "array"}, {"type": "list", "items": {"type": "string"}}]:
            with self.subTest(spec=spec):
                self.edit_json(self.skill / "skill.json",
                               lambda d: d["inputs"].append({"name": "extra", "description": "Extra.", **spec}))
                self.assert_fails("skill.json schema")
                shutil.copy(FIXTURE / "skills" / "demo" / "skill.json", self.skill / "skill.json")

    def test_typed_inputs_pass(self):
        team = {"name": "team", "description": "The team.", "type": "object",
                "properties": {"developers": {"type": "integer", "minimum": 1}},
                "default": {"developers": 10}}
        names = {"name": "names", "description": "Names.", "type": "array",
                 "items": {"type": "string"}, "default": []}
        self.edit_json(self.skill / "skill.json", lambda d: d["inputs"].extend([team, names]))
        self.assertEqual([], self.run_checks().failures)

    def test_input_default_matches_type(self):
        for spec in [{"type": "integer", "default": 1.5},
                     {"type": "number", "maximum": 10, "default": 11},
                     {"type": "object", "properties": {"developers": {"type": "integer"}}, "default": {}},
                     {"type": "object", "properties": {"developers": {"type": "integer"}},
                      "default": {"developers": 1, "other": 2}},
                     {"type": "array", "items": {"type": "string"}, "default": [1]}]:
            with self.subTest(spec=spec):
                self.edit_json(self.skill / "skill.json",
                               lambda d: d["inputs"].append({"name": "extra", "description": "Extra.", **spec}))
                self.assert_fails("inputs")
                shutil.copy(FIXTURE / "skills" / "demo" / "skill.json", self.skill / "skill.json")

    def test_input_with_default_is_not_required(self):
        self.edit_json(self.skill / "skill.json", lambda d: d["inputs"][0].update(default=1))
        self.assert_fails("inputs")

    def test_referenced_files(self):
        self.edit_json(self.skill / "skill.json", lambda d: d.update(templates=["templates/missing.md"]))
        self.assert_fails("referenced files")

    def test_catalog_out_of_date(self):
        self.edit_json(self.skill / "skill.json", lambda d: d.update(summary="A new summary."))
        self.assert_fails("catalog up to date")

    def test_catalog_fix(self):
        self.edit_json(self.skill / "skill.json", lambda d: d.update(summary="A new summary."))
        self.run_checks(fix=True)
        self.assertEqual([], self.run_checks().failures)
        catalog = json.loads((self.root / "catalog.json").read_text())
        self.assertEqual("A new summary.", catalog["skills"][0]["summary"])

    def test_catalog_fix_keeps_version(self):
        self.edit_json(self.root / "catalog.json", lambda d: d.update(version="2.3.4", skills=[]))
        self.run_checks(fix=True)
        self.assertEqual("2.3.4", json.loads((self.root / "catalog.json").read_text())["version"])

    def test_catalog_version(self):
        for version in [None, "1.0"]:
            with self.subTest(version=version):
                self.edit_json(self.root / "catalog.json",
                               lambda d: d.pop("version") if version is None else d.update(version=version))
                self.assert_fails("catalog version")

    def test_catalog_missing_skill(self):
        self.edit_json(self.root / "catalog.json", lambda d: d.update(skills=[]))
        self.assert_fails("catalog up to date")

    def test_data_schema_invalid(self):
        self.edit_json(self.skill / "report-data.schema.json", lambda d: d.update(type="nonsense"))
        self.assert_fails("data schema")

    def test_data_schema_wrong_id(self):
        self.edit_json(self.skill / "report-data.schema.json",
                       lambda d: d.update({"$id": "codescene://skills/other/report-data.schema.json"}))
        self.assert_fails("data schema")

    def test_examples(self):
        self.edit_json(self.skill / "examples" / "sample.report.json", lambda d: d["files"][0].pop("health"))
        self.assert_fails("examples")

    def test_renderer_markers(self):
        path = self.skill / "renderers" / "report.html"
        path.write_text(path.read_text().replace("<!-- {{/REPORT_DATA}} -->", ""))
        self.assert_fails("renderer markers")

    def test_renderer_marker_text_in_script_is_not_a_marker(self):
        path = self.skill / "renderers" / "report.html"
        path.write_text(path.read_text().replace(
            "data.project;", 'data.project || "Fill the {{REPORT_DATA}} block.";'))
        self.assertEqual([], self.run_checks().failures)

    def test_self_contained_renderer(self):
        path = self.skill / "renderers" / "report.html"
        for external in ['<script src="https://cdn.example.com/d3.js"></script>',
                         '<link rel="stylesheet" href="style.css">',
                         "<style>@import 'theme.css';</style>",
                         "<script>fetch('/data.json')</script>"]:
            with self.subTest(external=external):
                original = path.read_text()
                path.write_text(original.replace("</body>", external + "\n</body>"))
                self.assert_fails("self-contained renderer")
                path.write_text(original)

    def test_mcp_tools_mentioned(self):
        self.edit_json(self.skill / "skill.json",
                       lambda d: d["mcp_tools"].append("estimate_engineering_outcomes"))
        self.assert_fails("mcp tools mentioned")

    def test_templates_input_must_be_placeholder(self):
        path = self.skill / "templates" / "project-notes.md"
        path.write_text(path.read_text().replace("| Project id | {{project-id}} |", "| Project id | 42 |"))
        self.assert_fails("templates are templates")

    def test_templates_filled_value_outside_inputs_warns(self):
        self.append(self.skill / "templates" / "project-notes.md", "- Owner: Platform team\n")
        report = self.run_checks()
        self.assertEqual([], report.failures)
        self.assertEqual(["templates are templates"], [w.rule for w in report.warnings])

    def test_links(self):
        (self.root / "README.md").write_text("# Readme\n")
        (self.skill / "notes.md").write_text("# Notes\n")
        for link in ["missing.md", "renderers/", "/etc/hosts", "file:///etc/hosts",
                     "../../README.md", "../../../outside.md", "notes.md"]:
            with self.subTest(link=link):
                original = (self.skill / "SKILL.md").read_text()
                self.append(self.skill / "SKILL.md", f"See [this]({link}).\n")
                self.assert_fails("links")
                (self.skill / "SKILL.md").write_text(original)

    def test_links_that_pass(self):
        self.append(self.skill / "SKILL.md",
                    "See [the docs](https://example.com/docs), [rules](../../shared/ground-rules.md#top), "
                    "![chart](renderers/report.html) and `[not a link](missing.md)`.\n"
                    "```\n[also not a link](missing.md)\n```\n")
        self.assertEqual([], self.run_checks().failures)

    def test_code_span_naming_a_library_file(self):
        for code in ["renderers/report.html", "shared/ground-rules.md", "../../shared/ground-rules.md"]:
            with self.subTest(code=code):
                original = (self.skill / "SKILL.md").read_text()
                self.append(self.skill / "SKILL.md", f"Open `{code}`.\n")
                self.assert_fails("links")
                (self.skill / "SKILL.md").write_text(original)

    def test_shared_doc_links(self):
        self.append(self.root / "shared" / "ground-rules.md", "See [the guide](guide.md).\n")
        self.assert_fails("links")

    def test_template_links(self):
        self.append(self.skill / "templates" / "project-notes.md", "See [the rules](../../../shared/ground-rules.md).\n")
        self.assert_fails("links")

    # --- No-project-specifics guard ---

    def test_email(self):
        self.append(self.skill / "SKILL.md", "Ask jane.doe@acme.com for access.\n")
        self.assert_fails("email address")

    def test_allowed_emails(self):
        self.append(self.skill / "SKILL.md", "Write to someone@example.com or noreply@acme.com.\n")
        self.assertEqual([], self.run_checks().failures)

    def test_local_path(self):
        self.append(self.skill / "SKILL.md", "Save it to /Users/jane/reports.\n")
        self.assert_fails("local path")

    def test_codescene_url(self):
        self.append(self.skill / "SKILL.md", "See https://codescene.io/projects/4711/jobs.\n")
        self.assert_fails("CodeScene URL")

    def test_allow_marker_with_reason(self):
        self.append(self.skill / "SKILL.md",
                    "Save it to /Users/name/reports. <!-- allow-specifics: generic macOS example -->\n")
        report = self.run_checks()
        self.assertEqual([], report.failures)
        self.assertEqual(["generic macOS example"], [m.message for m in report.allow_markers])

    def test_allow_marker_without_reason(self):
        self.append(self.skill / "SKILL.md", "Save it to /Users/name/reports. <!-- allow-specifics -->\n")
        self.assert_fails("allow marker")

    def test_changed_from_scans_only_changed_files(self):
        git = lambda *args: subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "base")
        git("tag", "base")
        self.append(self.skill / "SKILL.md", "Ask jane.doe@acme.com for access.\n")
        git("add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "-m", "change")
        self.assert_fails("email address", changed_from="base")
        self.append(self.root / "shared" / "ground-rules.md", "Old contact: old@acme.com\n")
        report = self.run_checks(changed_from="HEAD")
        self.assertNotIn("email address", report.rules_failed())


if __name__ == "__main__":
    unittest.main()
