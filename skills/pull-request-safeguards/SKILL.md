---
name: codescene-pull-request-safeguards
description: Builds a report on how Code Health safeguards work on a CodeScene project's pull requests. It shows how often the pull request review catches an issue, how many findings authors fix rather than ignore or suppress, the trend week by week, and the same figures per developer and per pull request. Uses the CodeScene MCP server. Use when the user asks about pull request reviews, Code Health gates, PR safeguards, ignored or suppressed findings, or which developers' pull requests get flagged.
disable-model-invocation: true
---

# Pull request safeguards report

Produces a one-page report on CodeScene's Code Health review of pull requests in one project. Each pull request is reviewed before it merges. When the review **detects** a finding, the author can **fix** it, **ignore** it and merge anyway, or **suppress** it as accepted. The report shows how often the review catches something, what authors do about it, and where findings are left unresolved.

The data comes from `get_pull_request_safeguard_outcomes`: one row per pull request from the latest analysis, not live telemetry.

The report lists developers by name. Never show email addresses or account ids.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}-pull-request-safeguards.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project | required: its name or its id. Resolve a name to the id with `list_projects`; if several projects match, ask the user which one |
| Display name for the title | the project name from `list_projects` |
| Days | `30`: the last 30 days up to today |
| Author names | from the project notes: aliases to merge and bot accounts |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch the pull request outcomes
- [ ] 3. Merge author aliases and mark bots
- [ ] 4. Fill the report data and render the report
- [ ] 5. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tool `get_pull_request_safeguard_outcomes`. The server's namespace prefix varies between clients. If it is missing, ask the user to connect and authorize the CodeScene MCP server, or to reconnect it if it was updated, and stop.

**2. Fetch the outcomes.** Call `get_pull_request_safeguard_outcomes` with the project id, `from` set to `days` before today, `to` set to today, and `page_size` 1000. While the result has a `nextPageToken`, call again with it as `page_token` and the same other arguments, until every page is read. Then fetch the range of the same length just before, the same way.

Map each outcome to a `PullRequest`:

| `PullRequest` | Field |
|---|---|
| `id`, `repository` | `prId`, `repository` |
| `analysedAt` | `analysisDate`, as YYYY-MM-DD |
| `authors` | `authors`, after step 3 |
| `detected`, `fixed`, `ignored`, `suppressed` | `statistics.findingsDetected`, `findingsFixed`, `findingsIgnored`, `findingsSuppressed` |
| `status` | `interpretation.status` |

Set `range` to the dates you asked for. Put the earlier range in `previous` only if its earliest pull request falls within its first week; otherwise the data doesn't reach back that far, so leave `previous` out and say so in `notes`.

**3. Merge author aliases and mark bots.** The same person can appear under several names, such as a display name and a login. Use the aliases in the project notes. Otherwise, list names that look like the same person and ask the user which to merge; don't guess. Replace each alias with one display name, and list each name once per pull request. Put automation accounts, such as names ending in `[bot]`, in `bots`.

**4. Render.** Build a `ReportData` object that validates against the schema, with `project` (`name`, `source`, `id`), `generatedAt` and `notes`. Copy the renderer to the user's output location as `{{project-slug}}-pull-request-safeguards.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the charts appear instead of an error box.

Use `notes` for facts the reader needs, for example which author names were merged.

**5. Record specifics.** Create or update the project notes from the template, including the alias merges and bots, so the next run uses them.

## How the renderer reads the data

- **Summary tiles:** pull requests reviewed, how many had findings, the share of findings fixed, and pull requests left unresolved. With `previous`, each tile shows the change.
- **Week by week:** pull requests per week, split into no issues, resolved and unresolved, with the findings fixed, ignored and suppressed. Hovering a week shows its dates, active developers, pull requests by outcome and findings.
- **Developers:** a sortable table of each person's pull requests, those with findings, and the findings detected, fixed, ignored and suppressed. A pull request with two authors counts for both. Bots are listed below the table.
- **Pull requests with findings:** unresolved ones first, then by findings detected.
- **Repositories:** shown when the project has more than one.

## Rules learned the hard way

- **Never show email addresses.** Map author names only, and merge aliases into a display name.
- **Read every page.** The tool pages its results; a report built from the first page alone undercounts.
- **This is the analysis snapshot, not telemetry.** Pull requests after the latest analysis are missing. Show the range and the generation date in the report.
- **Don't mix in `get_pull_request_safeguard_insights`.** Its monthly totals can differ slightly from the per pull request rows, and two sources for the same figure confuse readers.
- Use CodeScene's theme colours, as in the other reports.

## Troubleshooting

- **The tool is missing although the server is connected:** the server may have been updated after the session connected. Ask the user to reconnect the CodeScene MCP server, then search again.
- **No pull requests:** the pull request integration isn't set up for this project, or no pull request was analysed in the range. The report says so.
