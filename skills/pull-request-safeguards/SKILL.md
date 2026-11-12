---
name: codescene-pull-request-safeguards
description: Builds a report on how Code Health safeguards work on a CodeScene project's pull requests. It shows how often the pull request review catches an issue, how many findings authors fix rather than ignore or suppress, whether each pull request maintained Code Health, the trend week by week, and the same figures per developer and per pull request. Uses the CodeScene MCP server. Use when the user asks about pull request reviews, Code Health gates, PR safeguards, ignored or suppressed findings, or which developers' pull requests get flagged.
disable-model-invocation: true
---

# Pull request safeguards report

Produces a one-page report on CodeScene's Code Health review of pull requests in one project. Each pull request is reviewed before it merges. When the review **detects** a finding, the author can **fix** it, **ignore** it and merge anyway, or **suppress** it as accepted. The report shows how often the review catches something, what authors do about it, where findings are left unresolved, and whether each pull request maintained, improved or lowered Code Health.

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
| Stable band | `0.05`: a pull request whose Code Health change is smaller than this, in either direction, maintained Code Health |
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
| `files` | `size`, when present: files added, modified or deleted, each counted once |
| `reviews` | `codeHealth.checks`: how many times the pull request was analysed. It is not a file count |
| `codeHealth.before`, `codeHealth.change` | `codeHealth.before` when present, `codeHealth.change` |
| `codeHealth.lowest` | `codeHealth.worst`: `score` and `file` |
| `codeHealth.degradedFiles`, `improvedFiles`, `newLowHealthFiles`, `degradationsLaterFixed` | the fields of the same names under `codeHealth` |

`size` and `codeHealth` are optional: older analyses and some pull requests have neither, or `size` alone. Leave out what the tool leaves out; never fill in a 0.

`change` is not an after score minus `before`, and there is no after score. It is the lines-of-code weighted mean of each remaining file's move, with a new file measured from 10.0, so a pull request that adds files can show a change that doesn't match `before`. Don't compute an after score from the two.

Set `range` to the dates you asked for. Put the earlier range in `previous` only if its earliest pull request falls within its first week; otherwise the data doesn't reach back that far, so leave `previous` out and say so in `notes`.

**3. Merge author aliases and mark bots.** The same person can appear under several names, such as a display name and a login. Use the aliases in the project notes. Otherwise, list names that look like the same person and ask the user which to merge; don't guess. Replace each alias with one display name, and list each name once per pull request. Put automation accounts, such as names ending in `[bot]`, in `bots`.

**4. Render.** Build a `ReportData` object that validates against the schema, with `project` (`name`, `source`, `id`), `generatedAt`, `stableBand` and `notes`. Copy the renderer to the user's output location as `{{project-slug}}-pull-request-safeguards.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the charts appear instead of an error box.

Use `notes` for facts the reader needs, for example which author names were merged.

**5. Record specifics.** Create or update the project notes from the template, including the alias merges and bots, so the next run uses them.

## How the renderer reads the data

- **Summary tiles:** pull requests reviewed, how many had findings, the share of findings fixed, and pull requests left unresolved. With `previous`, each tile shows the change.
- **Week by week:** pull requests per week, split into no issues, resolved and unresolved, with the findings fixed, ignored and suppressed. Hovering a week shows its dates, active developers, pull requests by outcome and findings.
- **Developers:** a sortable table of each person's pull requests, those with findings, the findings detected, fixed, ignored and suppressed, and the pull requests that improved or lowered Code Health. A pull request with two authors counts for both. Bots are listed below the table.
- **Code Health impact:** each measured pull request is **maintained** when its change is inside the stable band, and **improved** or **declined** when it is outside. A summary tile shows the share maintained or improved, and a panel in the weekly chart shows the improved and declined pull requests per week. Pull requests without impact data are left out of both.
- **Pull requests to look at:** only those that merged with a finding left in the code: unresolved ones, with ignored findings, first, then those with suppressed findings. Resolved pull requests are never listed; their findings were fixed. Each shows its files changed, how many times it was reviewed, its impact and the lowest-scoring file it touched.
- **Repositories:** shown when the project has more than one.

## Rules learned the hard way

- **Never show email addresses.** Map author names only, and merge aliases into a display name.
- **Read every page.** The tool pages its results; a report built from the first page alone undercounts.
- **This is the analysis snapshot, not telemetry.** Pull requests after the latest analysis are missing. Show the range and the generation date in the report.
- **Don't mix in `get_pull_request_safeguard_insights`.** Its monthly totals can differ slightly from the per pull request rows, and two sources for the same figure confuse readers.
- **A small change is good news.** A change inside the stable band means the pull request kept Code Health where it was; show it as maintained, never as a small decline or a decimal trend. Call out only changes outside the band.
- **Don't show the change as a number.** Readers compare decimals they can't interpret. Show maintained, improved or declined, and the lowest-scoring file touched for context.
- **The lowest file touched may predate the pull request.** A pull request that edits an 8.3 file without changing it still maintained Code Health. Don't blame it for the score.
- Use CodeScene's theme colours, as in the other reports.

## Troubleshooting

- **The tool is missing although the server is connected:** the server may have been updated after the session connected. Ask the user to reconnect the CodeScene MCP server, then search again.
- **No pull requests:** the pull request integration isn't set up for this project, or no pull request was analysed in the range. The report says so.
