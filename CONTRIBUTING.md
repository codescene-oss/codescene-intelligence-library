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
- **Link library files, don't name them.** In `SKILL.md` and `shared/*.md`, every file an agent should open is a relative Markdown link to a file in the library, such as `[renderers/report.html](renderers/report.html)` or `[ground rules](../../shared/ground-rules.md)`. No absolute paths, no links outside `catalog.json`, `LICENSE`, `shared/` and `skills/`, and no library paths in `code spans`. The CodeScene MCP server rewrites these links to `codescene-library://` resources, so a link that breaks the rule breaks the skill there. Paths in the user's workspace are not library files, so write them as `code`. Templates have no links, since they are copied into the user's workspace.
- **Keep renderers self-contained.** One HTML file with inline CSS, JS and SVG. No external scripts, stylesheets, fonts or network calls.
- **`skill.json` is the source of truth** for a skill's metadata. Don't edit `catalog.json` by hand; regenerate it (see below).
- **Don't change versions.** Maintainers decide when a release happens and set versions then.
- **One skill per pull request**, so each can be reviewed and released on its own.

## Adding a skill

Follow the folder layout in the [README](README.md#adding-a-skill). In short: create `skills/<id>/` with `SKILL.md`, `skill.json`, `report-data.schema.json`, `renderers/`, `templates/` and `examples/`. List every MCP tool the skill calls in `skill.json`, and add the skill to the README.

In `skill.json`:

- **`inputs`** become the arguments of the skill's MCP prompt, which users fill in from a slash command. Give each a `name`, a `description` users will read, and a `type`: `integer`, `number`, `boolean`, `string`, `array` (with `items`) or `object` (with `properties`, all of them required). Add `minimum`, `maximum` or `enum` where they apply. An input has either a `default`, which must match its type, or `"required": true`.
- **`min_server_version`** is the lowest version of the `codescene-projects` MCP server that has every tool and argument the skill uses. Older servers hide the skill. Use `1.0.0` unless the skill needs something newer.

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

- **Structure:** the skill folder layout, `skill.json` against its schema, that every referenced file exists, that each input's default matches its type, and that `catalog.json` matches the `skill.json` files and has a version.
- **Links:** every link in `SKILL.md` and `shared/*.md` resolves to a file the release ships, and every file a `SKILL.md` links to is listed in its `skill.json`. A library path in a `code span` fails, and so does any link in a template.
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

## Releases

Maintainers release from `main`:

1. In a pull request, set the top-level `version` in `catalog.json`. `--fix` keeps it when it regenerates the catalog.
2. After it merges, tag that commit `v<version>` and push the tag.

The release workflow then builds `codescene-intelligence-library-<version>.zip` with `catalog.json`, `LICENSE`, `shared/` and `skills/` at its root, plus a `MANIFEST.json` with the sha256 of every file. It attaches the zip, its `.sha256` and a build provenance attestation to the GitHub release. It runs no checks, since every pull request is validated before it merges. It stops only if the tag isn't `v` plus the catalog's version.

To build the same zip locally from `HEAD`:

```bash
python scripts/build_release.py
```
