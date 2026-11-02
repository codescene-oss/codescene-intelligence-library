# Contributing

Thanks for helping build the CodeScene intelligence library. This guide covers what we accept, the rules every contribution follows, and how to check your work before you open a pull request.

## What we accept

- New skills that turn CodeScene's MCP analysis into a report.
- Improvements to existing skills: clearer workflows, better renderers, richer report data.
- Fixes to schemas, examples, templates and docs.

For a new skill, open an issue first describing the report and who it is for. That saves you building something that overlaps an existing skill.

## Rules for every contribution

- **Keep it generic.** No project names, people, repository names or numbers from a real analysis, anywhere: skills, templates, examples or docs. Project-specific inputs live in the user's own workspace, created from a skill's `templates/`.
- **Follow the [ground rules](shared/ground-rules.md).** Skills use only data returned by CodeScene's MCP tools, and never invent scores, counts or outcomes.
- **Keep renderers self-contained.** One HTML file with inline CSS, JS and SVG. No external scripts, stylesheets, fonts or network calls.
- **`skill.json` is the source of truth** for a skill's metadata. Don't edit `catalog.json` by hand; regenerate it (see below).
- **Don't change versions.** Maintainers decide when a release happens and set versions then.
- **One skill per pull request**, so each can be reviewed and released on its own.

## Adding a skill

Follow the folder layout in the [README](README.md#adding-a-skill). In short: create `skills/<id>/` with `SKILL.md`, `skill.json`, `report-data.schema.json`, `renderers/`, `templates/` and `examples/`. List every MCP tool the skill calls in `skill.json`, and add the skill to the README.

## Check your contribution

Every pull request runs the same checks as you can run locally. Running them first saves you a round trip.

Install the one dependency (Python 3.10 or later):

```bash
pip install -r scripts/requirements.txt
```

Run all checks:

```bash
python scripts/validate.py
```

Each failure is printed as `path: rule: what to fix`, grouped by file. If the catalog is out of date, regenerate it from the `skill.json` files:

```bash
python scripts/validate.py --fix
```

### Run the checks on every commit (optional)

The repository ships a [pre-commit](https://pre-commit.com) hook that runs the same script:

```bash
pip install pre-commit
```

```bash
pre-commit install
```

### What the checks cover

- **Structure:** the skill folder layout, `skill.json` against its schema, that every referenced file exists, and that `catalog.json` matches the `skill.json` files.
- **Data contracts:** each `report-data.schema.json` is a valid JSON Schema, and every file in `examples/` validates against it.
- **Renderers:** exactly one `{{REPORT_DATA}}` block, and no external resources.
- **MCP tools:** every tool listed in `skill.json` is described in `SKILL.md`.
- **Project data:** email addresses, local file paths, CodeScene project URLs, and filled-in values in a template's `## Inputs` table.

### False positives

If the project-data check flags something that is genuinely generic, add a comment on the same line saying why. In Markdown and HTML:

```html
<!-- allow-specifics: why this is not project data -->
```

In JavaScript and CSS, use `// allow-specifics: ...` or `/* allow-specifics: ... */`. A marker without a reason fails the check. Every marker is listed in the pull request's check summary, and reviewers will ask about any whose reason doesn't hold.

## Pull requests

- The `validate` check must pass before a pull request can be merged.
- A maintainer reviews every pull request. Review covers what the checks can't: real names or data, whether a skill's workflow makes sense, and whether the report is useful.
- Maintainers merge, and decide when the change goes into a release.
