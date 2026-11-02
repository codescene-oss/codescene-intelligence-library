#!/usr/bin/env python3
"""Checks that the library follows its contract and holds no project-specific data.

Runs the same checks locally and in CI:

    python scripts/validate.py                       # every check, whole tree
    python scripts/validate.py --fix                 # regenerate catalog.json from the skill.json files
    python scripts/validate.py --changed-from REF    # scan only files changed since REF for project data

Each failure is printed as `path: rule: what to fix`, grouped by file. Exits 1 on any failure.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

REQUIRED_FILES = ["SKILL.md", "skill.json", "report-data.schema.json"]
REQUIRED_DIRS = ["renderers", "templates", "examples"]

TEXT_SUFFIXES = {".md", ".json", ".html", ".htm", ".js", ".css", ".svg", ".txt", ".yml", ".yaml"}
# Tooling, not library content: the validator's own patterns and test fixtures would trip the guard.
GUARD_EXCLUDED_DIRS = {"scripts"}

REPORT_DATA_OPEN = re.compile(r"<!--\s*\{\{REPORT_DATA\}\}")
REPORT_DATA_CLOSE = re.compile(r"<!--\s*\{\{/REPORT_DATA\}\}\s*-->")

EXTERNAL_RESOURCES = [
    (re.compile(r"<script\b[^>]*\bsrc\s*=", re.I), "<script src>"),
    (re.compile(r"<link\b[^>]*\bhref\s*=", re.I), "<link href>"),
    (re.compile(r"\bsrc\s*=\s*[\"']?https?://", re.I), "remote src"),
    (re.compile(r"@import\b", re.I), "@import"),
    (re.compile(r"url\(\s*[\"']?https?://", re.I), "remote url()"),
    (re.compile(r"\bfetch\s*\("), "fetch()"),
    (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
]

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
ALLOWED_EMAIL = re.compile(r"^noreply@|@example\.(com|org)$", re.I)
PROJECT_DATA = [
    (re.compile(r"/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\"), "local path",
     "replace the local path with a generic one or a {{placeholder}}"),
    (re.compile(r"https?://[^\s\"'<>)]*/projects/\d+"), "CodeScene URL",
     "remove the link to a real CodeScene project"),
]
ALLOW_MARKER = re.compile(r"(?:<!--|//|/\*)\s*allow-specifics\b:?(?P<reason>.*?)(?:-->|\*/|$)")
PLACEHOLDER = re.compile(r"\{\{[^}]+\}\}")
SECTION_HEADING = re.compile(r"^##\s+(.*?)\s*$")
LIST_ITEM_WITH_VALUE = re.compile(r"^\s*[-*]\s+[^:]+:\s+\S")


@dataclass(frozen=True)
class Finding:
    """One result of a check: where it is, which rule produced it, and what to do about it."""

    path: str
    rule: str
    message: str


class Report:
    """Collects everything a run finds.

    Failures fail the run. Warnings and allow markers are only shown, so a reviewer can judge them.
    """

    def __init__(self):
        self.failures = []
        self.warnings = []
        self.allow_markers = []

    def fail(self, path, rule, message):
        """Records a broken rule that must be fixed before merging."""
        self.failures.append(Finding(str(path), rule, message))

    def warn(self, path, rule, message):
        """Records something that looks wrong but may be fine; it doesn't fail the run."""
        self.warnings.append(Finding(str(path), rule, message))

    def rules_failed(self):
        """The names of the rules that failed, mainly for tests."""
        return {f.rule for f in self.failures}


# --- File helpers -------------------------------------------------------------


def rel(root, path):
    """The path as contributors see it: relative to the repo root, with forward slashes."""
    return path.relative_to(root).as_posix()


def load_json(root, path, report):
    """Parses a JSON file, reporting unreadable or invalid files as failures instead of crashing.

    Returns None when the file can't be used, so callers can skip the checks that depend on it.
    """
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        report.fail(rel(root, path), "json", f"invalid JSON at line {e.lineno}: {e.msg}")
    except OSError as e:
        report.fail(rel(root, path), "json", f"cannot read: {e.strerror}")
    return None


def numbered_lines(path):
    """Yields (line number, line) pairs, so findings can point at the exact line."""
    yield from enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1)


def schema_errors(validator, data):
    """Yields each JSON Schema violation as (location, message), in document order.

    The location is a slash-separated path into the data, or "(root)", so a contributor can find the field.
    """
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        yield "/".join(str(p) for p in error.path) or "(root)", error.message


def skill_dirs(root):
    """The folders under skills/, one per skill, in a stable order."""
    skills = root / "skills"
    if not skills.is_dir():
        return []
    return sorted(p for p in skills.iterdir() if p.is_dir() and not p.name.startswith("."))


# --- Integrity checks ---------------------------------------------------------


def check_layout(root, skill_dir, report):
    """Every skill has the same folder layout, so clients and contributors know where to find each part."""
    for name in REQUIRED_FILES:
        if not (skill_dir / name).is_file():
            report.fail(rel(root, skill_dir), "layout", f"missing {name}")
    for name in REQUIRED_DIRS:
        if not (skill_dir / name).is_dir():
            report.fail(rel(root, skill_dir), "layout", f"missing {name}/")


def check_skill_json(root, skill_dir, skill_schema, report):
    """Validates a skill's metadata against schemas/skill.schema.json and its folder name.

    Returns the metadata only when it is valid, because the remaining checks rely on its fields.
    """
    path = skill_dir / "skill.json"
    if not path.is_file():
        return None
    meta = load_json(root, path, report)
    if meta is None:
        return None
    errors = list(schema_errors(Draft202012Validator(skill_schema), meta))
    for where, message in errors:
        report.fail(rel(root, path), "skill.json schema", f"{where}: {message}")
    if errors:
        return None
    if meta["id"] != skill_dir.name:
        report.fail(rel(root, path), "folder id", f'id "{meta["id"]}" differs from folder "{skill_dir.name}"; rename one')
    return meta


def referenced_paths(meta):
    """Every file path a skill.json points at, relative to the skill's folder."""
    return ([meta["skill"], meta["data_schema"]]
            + [r["file"] for r in meta["renderers"]]
            + meta["templates"] + meta["shared"] + meta["examples"])


def check_referenced_files(root, skill_dir, meta, report):
    """Every file the metadata names exists, so clients that follow skill.json never hit a dead path."""
    for ref in referenced_paths(meta):
        if not (skill_dir / ref).is_file():
            report.fail(rel(root, skill_dir / "skill.json"), "referenced files", f"{ref}: not found")


def check_data_schema(root, skill_dir, meta, report):
    """The report-data schema is a valid draft 2020-12 schema and carries its skill's $id.

    Returns the schema when it is usable, so the examples can be validated against it.
    """
    path = skill_dir / meta["data_schema"]
    if not path.is_file():
        return None
    schema = load_json(root, path, report)
    if schema is None:
        return None
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as e:
        report.fail(rel(root, path), "data schema", f"not a valid draft 2020-12 schema: {e.message}")
        return None
    expected_id = f"codescene://skills/{skill_dir.name}/report-data.schema.json"
    if schema.get("$id") != expected_id:
        report.fail(rel(root, path), "data schema", f'$id must be "{expected_id}"')
    return schema


def check_examples(root, skill_dir, meta, schema, report):
    """Each example validates against the data schema, so the samples prove the contract they document."""
    validator = Draft202012Validator(schema)
    for ref in meta["examples"]:
        path = skill_dir / ref
        if not path.is_file():
            continue
        data = load_json(root, path, report)
        if data is None:
            continue
        for where, message in schema_errors(validator, data):
            report.fail(rel(root, path), "examples", f"{where}: {message}")


def check_report_data_markers(root, path, text, report):
    """A renderer has exactly one {{REPORT_DATA}} block, so clients know exactly what to replace.

    Only the HTML comment markers count; the placeholder mentioned in a string or error message does not.
    """
    opens, closes = len(REPORT_DATA_OPEN.findall(text)), len(REPORT_DATA_CLOSE.findall(text))
    if opens != 1 or closes != 1:
        report.fail(rel(root, path), "renderer markers",
                    f"needs exactly one {{{{REPORT_DATA}}}} / {{{{/REPORT_DATA}}}} comment pair, found {opens} / {closes}")


def check_self_contained(root, path, report):
    """A renderer loads nothing from outside its own file, so a report works offline and leaks nothing.

    Pattern-based: it catches accidents, not deliberate evasion. Each hit names its line.
    """
    for lineno, line in numbered_lines(path):
        for pattern, label in EXTERNAL_RESOURCES:
            if pattern.search(line):
                report.fail(f"{rel(root, path)}:{lineno}", "self-contained renderer",
                            f"{label} loads an external resource; inline it instead")


def check_renderers(root, skill_dir, meta, report):
    """Runs the renderer checks on every renderer the skill declares."""
    for renderer in meta["renderers"]:
        path = skill_dir / renderer["file"]
        if not path.is_file():
            continue
        check_report_data_markers(root, path, path.read_text(encoding="utf-8"), report)
        check_self_contained(root, path, report)


def check_mcp_tools(root, skill_dir, meta, report):
    """Every MCP tool declared in skill.json is described in SKILL.md.

    Checked in this direction only: SKILL.md also names fields like `path`, so the reverse can't be matched reliably.
    """
    path = skill_dir / meta["skill"]
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for tool in meta["mcp_tools"]:
        if not re.search(rf"\b{re.escape(tool)}\b", text):
            report.fail(rel(root, skill_dir / "skill.json"), "mcp tools mentioned",
                        f"{tool} is declared but never mentioned in {meta['skill']}; describe how it is used or remove it")


def is_table_value_row(line):
    """True for a Markdown table row that holds values: not the header row and not the |---| separator."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    is_separator = all(re.fullmatch(r":?-+:?", c) for c in cells)
    is_header = cells[:1] == ["Input"]
    return not (is_separator or is_header)


def check_template_line(where, section, line, report):
    """A template line holds a {{placeholder}} where a project would fill in its own value.

    Under `## Inputs` this is a hard rule. Elsewhere, a `- Label: value` line without one is only
    a warning, because templates may legitimately carry fixed guidance text.
    """
    if PLACEHOLDER.search(line):
        return
    if section == "inputs" and line.startswith("|"):
        if is_table_value_row(line):
            report.fail(where, "templates are templates", "input value must be a {{placeholder}}")
    elif LIST_ITEM_WITH_VALUE.match(line):
        report.warn(where, "templates are templates", "looks like a filled-in value; use a {{placeholder}}")


def check_templates(root, skill_dir, meta, report):
    """Templates hold placeholders, never a real project's values, so they stay generic.

    Tracks the current `##` section while reading, since the rule is stricter under `## Inputs`.
    """
    for ref in meta["templates"]:
        path = skill_dir / ref
        if not path.is_file():
            continue
        section = None
        for lineno, line in numbered_lines(path):
            heading = SECTION_HEADING.match(line)
            if heading:
                section = heading.group(1).lower()
            else:
                check_template_line(f"{rel(root, path)}:{lineno}", section, line, report)


def check_skill(root, skill_dir, skill_schema, report):
    """Runs every integrity check on one skill.

    Returns its metadata when valid, for building the catalog. Checks that need valid metadata, or a
    valid data schema, are skipped when those are broken, so one mistake doesn't cascade into many.
    """
    check_layout(root, skill_dir, report)
    meta = check_skill_json(root, skill_dir, skill_schema, report)
    if meta is None:
        return None
    check_referenced_files(root, skill_dir, meta, report)
    schema = check_data_schema(root, skill_dir, meta, report)
    if schema is not None:
        check_examples(root, skill_dir, meta, schema, report)
    check_renderers(root, skill_dir, meta, report)
    check_mcp_tools(root, skill_dir, meta, report)
    check_templates(root, skill_dir, meta, report)
    return meta


# --- Catalog ------------------------------------------------------------------


def catalog_entry(meta):
    """The catalog's view of one skill: the fields clients need to find and fetch it, taken from skill.json."""
    return {
        "id": meta["id"],
        "version": meta["version"],
        "path": f"skills/{meta['id']}",
        "summary": meta["summary"],
        "renderers": [r["id"] for r in meta["renderers"]],
    }


def catalog_order(metas, current):
    """Sorts skills in their current catalog order, with new skills last, so regenerating causes no churn."""
    order = [entry.get("id") for entry in (current or {}).get("skills", [])]
    rank = lambda m: (order.index(m["id"]) if m["id"] in order else len(order), m["id"])
    return sorted(metas, key=rank)


def build_catalog(metas, current):
    """The catalog generated from the skill.json files, which are its single source of truth."""
    return {"skills": [catalog_entry(m) for m in catalog_order(metas, current)]}


def catalog_text(catalog):
    """The catalog serialized exactly as committed, so a byte comparison detects any drift."""
    return json.dumps(catalog, indent=2, ensure_ascii=False) + "\n"


def check_catalog(root, metas, report, fix):
    """catalog.json matches what the skill.json files generate; with fix, rewrites it instead of failing."""
    path = root / "catalog.json"
    current = load_json(root, path, report) if path.is_file() else None
    if path.is_file() and current is None:
        return
    expected = catalog_text(build_catalog(metas, current))
    actual = path.read_text(encoding="utf-8") if path.is_file() else None
    if actual == expected:
        return
    if fix:
        path.write_text(expected, encoding="utf-8")
        print("catalog.json: regenerated from the skill.json files")
    else:
        report.fail("catalog.json", "catalog up to date", "out of date; run python scripts/validate.py --fix")


# --- No-project-specifics guard -----------------------------------------------


def changed_files(root, base):
    """Files added, copied, modified or renamed since the merge base with `base`; the diff a PR introduces."""
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout
    return [root / line for line in out.splitlines() if line]


def all_files(root):
    """Every file in the tree except hidden folders (such as .git) and node_modules."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "node_modules")
        files += [Path(dirpath) / f for f in sorted(filenames)]
    return files


def is_guarded(root, path):
    """True for library content worth scanning: an existing text file outside the tooling folders."""
    return (path.is_file() and path.suffix.lower() in TEXT_SUFFIXES
            and rel(root, path).split("/")[0] not in GUARD_EXCLUDED_DIRS)


def guarded_files(root, changed_from):
    """The files to scan for project data: only those a PR changed when `changed_from` is given, else all."""
    candidates = changed_files(root, changed_from) if changed_from else all_files(root)
    return [p for p in candidates if is_guarded(root, p)]


def handle_allow_marker(where, line, report):
    """Applies an allow-specifics marker on the line, if there is one.

    A marker with a reason is recorded for review and exempts the line. A marker without a reason
    fails, so every exemption is explained. Returns True when the line is exempt from the guard.
    """
    marker = ALLOW_MARKER.search(line)
    if not marker:
        return False
    reason = (marker.group("reason") or "").strip(" :")
    if reason:
        report.allow_markers.append(Finding(where, "allow-specifics", reason))
    else:
        report.fail(where, "allow marker", "allow-specifics needs a reason: allow-specifics: <why>")
    return True


def check_line_for_project_data(where, line, report):
    """Flags the shapes of real project data on one line: email addresses, local paths and project URLs.

    Names can't be pattern-matched, so customers, products and people are left to review.
    """
    for match in EMAIL.finditer(line):
        if not ALLOWED_EMAIL.search(match.group(0)):
            report.fail(where, "email address", f"{match.group(0)}: use an example.com address or remove it")
    for pattern, rule, fix in PROJECT_DATA:
        if pattern.search(line):
            report.fail(where, rule, fix)


def check_project_data(root, report, changed_from=None):
    """Scans library content for project-specific data, honouring allow-specifics markers line by line."""
    for path in guarded_files(root, changed_from):
        for lineno, line in numbered_lines(path):
            where = f"{rel(root, path)}:{lineno}"
            if not handle_allow_marker(where, line, report):
                check_line_for_project_data(where, line, report)


# --- Running ------------------------------------------------------------------


def load_skill_schema():
    """The contract for skill.json, read from schemas/ next to this script rather than from the checked root."""
    path = Path(__file__).resolve().parent.parent / "schemas" / "skill.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root, fix=False, changed_from=None):
    """Runs every check against the library at `root` and returns the Report.

    The catalog check comes after the skills because it is generated from their valid metadata.
    """
    root = Path(root).resolve()
    report = Report()
    skill_schema = load_skill_schema()
    metas = [m for m in (check_skill(root, d, skill_schema, report) for d in skill_dirs(root)) if m]
    check_catalog(root, metas, report, fix)
    check_project_data(root, report, changed_from)
    return report


def print_grouped(findings, stream):
    """Prints findings grouped under their file, so a contributor fixes one file at a time."""
    by_file = defaultdict(list)
    for f in findings:
        by_file[f.path.split(":")[0]].append(f)
    for file in sorted(by_file):
        print(file, file=stream)
        for f in by_file[file]:
            print(f"  {f.path}: {f.rule}: {f.message}", file=stream)


def write_step_summary(report):
    """In GitHub Actions, adds the counts and every allow marker to the job summary for reviewers."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    lines = ["## Validation", "", f"{len(report.failures)} failure(s), {len(report.warnings)} warning(s)."]
    if report.allow_markers:
        lines += ["", "### allow-specifics markers", "", "| Location | Reason |", "| --- | --- |"]
        lines += [f"| `{m.path}` | {m.message} |" for m in report.allow_markers]
    with open(summary, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def print_report(report):
    """Prints warnings and allow markers to stdout and failures to stderr. Returns the exit code."""
    if report.warnings:
        print(f"{len(report.warnings)} warning(s):")
        print_grouped(report.warnings, sys.stdout)
    if report.allow_markers:
        print(f"{len(report.allow_markers)} allow-specifics marker(s), for review:")
        print_grouped(report.allow_markers, sys.stdout)
    if report.failures:
        print(f"{len(report.failures)} failure(s):", file=sys.stderr)
        print_grouped(report.failures, sys.stderr)
        return 1
    print("All checks passed.")
    return 0


def parse_args(argv):
    """The command line. --root is hidden: it exists so the tests can point the checks at a fixture."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fix", action="store_true", help="regenerate catalog.json from the skill.json files")
    parser.add_argument("--changed-from", metavar="REF", help="scan only files changed since REF for project data")
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv=None):
    """Entry point: validate, report, and exit non-zero on any failure."""
    args = parse_args(argv)
    report = validate(args.root, fix=args.fix, changed_from=args.changed_from)
    write_step_summary(report)
    return print_report(report)


if __name__ == "__main__":
    sys.exit(main())
