---
name: codescene-mcp-safeguard-insights
description: Builds a report on how a CodeScene project's developers use the local Code Health MCP, from live product telemetry. It shows safeguard checks, Code Health degradations prevented before commit, Code Health uplifts, the trend over a year, the most active users, which MCP tools they rely on, and which installations are out of date. Uses the CodeScene MCP server. Use when the user asks about MCP usage, Code Health safeguard results, AI coding guardrails, or who uses the Code Health MCP.
disable-model-invocation: true
---

# MCP safeguard insights report

Produces a one-page report on the local Code Health MCP in one project: how much it is used, what it catches, and who uses it most. The local MCP checks Code Health while developers, or their AI coding assistants, write code. Each check can **prevent a degradation** (unhealthy code caught before it is committed) or record an **uplift** (a change that improves Code Health).

The data comes from `get_mcp_safeguard_insights`: live telemetry, not the latest analysis, so the numbers can change between runs without a new analysis.

The report names the most active users. It shows their names and check counts only: never email addresses or account ids, even though the tool returns them.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}-mcp-safeguard-insights.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project | required: its name or its id. Resolve a name to the id with `list_projects`; if several projects match, ask the user which one |
| Display name for the title | the project name from `list_projects` |
| Period | `monthly`: the last 30 days against the 30 before. `weekly` compares weeks |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch the safeguard insights
- [ ] 3. Fill the report data and render the report
- [ ] 4. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tool `get_mcp_safeguard_insights`. The server's namespace prefix varies between clients. If it is missing, ask the user to connect and authorize the CodeScene MCP server, or to reconnect it if it was updated, and stop.

**2. Fetch the insights.** Call `get_mcp_safeguard_insights` with the project id and the period. Map the result:

| `ReportData` | Field |
|---|---|
| `generatedAt` | `meta.generatedAt`, as YYYY-MM-DD |
| `period` | `meta.period` |
| `totals` | from `summary`: `numberOfUsers` → `users`, `numberOfActiveUsers` → `activeUsers`, `numberOfInstallations` → `installations`, `numberOfActiveInstallations` → `activeInstallations`, `numberOfSafeguardChecks` → `checks`, `numberOfUplifts` → `uplifts`, `numberOfDegradationsPrevented` → `degradationsPrevented` |
| `selected`, `previous` | `selectedPeriod` and `previousPeriod`, mapped as below |
| `versions` | `summary.versions` as `{ version, activeInstalls }` |
| `trend` | `trends.adoption` and `trends.impact` joined on `from`: `{ from, to, activeUsers, uplifts, degradationsPrevented }` |

Each period maps to a `Period`:

| `Period` | Field |
|---|---|
| `from`, `to` | `from`, `to` |
| `activeUsers`, `newUsers` | `summary.numberOfActiveUsers`, `summary.numberOfNewUsers` |
| `checks`, `uplifts`, `degradationsPrevented` | `summary.numberOfSafeguardChecks`, `summary.numberOfUplifts`, `summary.numberOfDegradationsPrevented` |
| `tools` | `summary.mostUsedTools` |
| `checksPerDeveloper` | `checksPerDeveloper` as `{ median, min, max, distribution }`, with `min` and `max` from `range` |
| `developers` | `checksPerDeveloper.topDevelopers` as `{ name, checks }`, from `name` and `count`. Drop `id` and `label`: the label is often an email address |

A project without usage returns zeros. Render it anyway: the report then says the MCP isn't in use yet.

**3. Render.** Build a `ReportData` object that validates against the schema, with `project` (`name`, `source`, `id`) and `notes`. Copy the renderer to the user's output location as `{{project-slug}}-mcp-safeguard-insights.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the charts appear instead of an error box.

Use `notes` for facts the reader needs, for example a developer who appears under a first name only.

**4. Record specifics.** Create or update the project notes from the template.

## How the renderer reads the data

- **Summary tiles:** active users, degradations prevented and uplifts in the selected period, each with the change from the previous one. The outcomes lead; check volume does not.
- **Over the year:** active users per period as bars, and the impact (degradations prevented and uplifts) per period.
- **Most active users:** the developers the tool lists, by checks in the selected period, with their checks in the previous period. Developers who were active before but not now are listed after them. The tool may not list every active user; the report says how many are missing.
- **Checks per developer:** the distribution across usage bands, now and before. A shift to the right means the MCP has become part of daily work.
- **Tools:** which MCP tools the checks came from.
- **Installations:** active installations per version. Installations not on the newest version that has active installations are flagged.
- **Totals:** at the end, the safeguard checks in the period and all-time figures, as context.

## Rules learned the hard way

- **Never show email addresses.** `topDevelopers[].label` is often an email address. Map the name only.
- **Telemetry is not the analysis.** These numbers can move between two runs on the same day. Show the period and the generation date in the report.
- **Versions add up to more than the installations.** One installation that upgraded during the period counts once for each version it ran. Show active installs per version, not a share.
- Use CodeScene's theme colours, as in the other reports.

## Troubleshooting

- **The tool is missing although the server is connected:** the server may have been updated after the session connected. Ask the user to reconnect the CodeScene MCP server, then search again.
- **Every number is zero:** no developer has used the MCP on this project yet. The report says so; suggest installing the local Code Health MCP.
