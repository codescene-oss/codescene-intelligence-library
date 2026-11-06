---
name: codescene-portfolio-overview
description: Builds a one-page overview of every CodeScene project the user can access, for technical leaders and managers. Places each project in a tier by hotspot Code Health (call to action below 4.0, needs attention below 9.0, healthy, and AI-optimal from 9.5), shows what works well and where attention is needed, and points to the deeper report for each project that needs it. Uses the CodeScene MCP server. Use when the user asks for a portfolio, organization-wide or all-projects summary, a management overview, or which projects need attention.
disable-model-invocation: true
---

# Portfolio overview report

Produces a one-page summary of all the CodeScene projects the user can access. It is written for a technical leader or manager and answers two questions: **what works well**, and **where is my attention needed**.

The report ranks projects by **hotspot Code Health**: the health of the code the teams change most, which decides how fast and safely they deliver. Each project lands in one tier:

| Tier | Hotspot Code Health | Where it appears |
|---|---|---|
| **Call to action** | below 4.0 | Top of *Where your attention is needed* |
| **Needs attention** | 4.0 to below 9.0 | *Where your attention is needed* |
| **Healthy** | 9.0 to below 9.5 | *What works well* |
| **AI-optimal** | 9.5 and up | *What works well*, as the main strength |

AI-optimal code is a common goal: it is where AI assistants and people both work at their best. CodeScene's own benchmarks call 9.5 *AI Friendly* and 10.0 *AI Optimal*; this report counts everything from 9.5 as AI-optimal.

Other signals are **flags**: they rank projects within a tier but never move them to another. A healthy project with flags goes on a *watch list* in the attention section.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. The renderer derives the tiers, flags, ranking and next steps from the data. Inputs and decisions for this portfolio go in the user's workspace, not in this library, as `codescene/portfolio/{{portfolio-slug}}-portfolio-overview.md`, created from [templates/portfolio-notes.md](templates/portfolio-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the portfolio notes if they exist; otherwise use the defaults and tell the user.

| Input | Default |
|---|---|
| Portfolio name for the title | ask the user, for example the organization's name |
| Maximum number of projects | 50, most recently analysed first |
| Name filter | none: every project |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. List the projects
- [ ] 3. Assess each project's Code Health
- [ ] 4. Fetch the file summary counts
- [ ] 5. Fetch the commit activity
- [ ] 6. Fetch the Code Health alerts
- [ ] 7. Fill the report data and render the report
- [ ] 8. Record the portfolio specifics
```

Steps 3 to 6 make four calls per project. Run independent calls in parallel where the client allows it.

**1. Check data access.** Find the CodeScene MCP tools `list_projects` and `assess_project_code_health`. The server's namespace prefix varies between clients. If they are missing, ask the user to connect and authorize the CodeScene MCP server, and stop. Use one server for the whole report.

**2. List the projects.** Call `list_projects` with `page_size: 1000` (and `name` when there is a name filter), following `nextPageToken`. Keep projects with `analysed: true`. Sort by `latestAnalysisAt`, newest first, and keep up to the maximum. Record the total in `projectCount`.

**3. Assess Code Health.** Call `assess_project_code_health` for each project. The result is large because of the series; read it with a JSON tool. If it returns an error, add the project with `available: false` and the error message, and skip steps 4 to 6 for it. Otherwise map from `codeHealth`:

| `Project` | Field |
|---|---|
| `hotspotHealth` | `hotspotCodeHealth.value`; `null` when `hotspotCodeHealth.classification` is null, which means no active hotspots (the value is then 0, not unhealthy code) |
| `averageHealth` | `averageCodeHealth.value` |
| `hotspotHealthYearAgo` | the value of the last point in `hotspotCodeHealth.series` dated on or before one year before `asOf`; `null` when the series starts later |
| `averageHealthYearAgo` | the same, from `averageCodeHealth.series` |
| `staleness` | `staleness.classification` |
| `codeAgeDays` | `staleness.codeAgeDays` |
| `languages` | `languages` as `{ name, linesOfCode }` |
| `linesOfCode` | the sum of `languages[].linesOfCode` |

Round Code Health to two decimals.

**4. Fetch the summary counts.** Call `explore_project_files` with `page_size: 1` and `sort: "linesOfCode:asc"` (the smallest file keeps the result short). From `summary`, map `totalFiles` to `files`, `hotspotCount` to `hotspots`, `healthyHotspotCount` to `healthyHotspots`, `upliftTargetCount` to `upliftTargets` and `offboardingRiskCount` to `offboardingRisks`.

**5. Fetch the commit activity.** Call `get_commit_activity` with `group_by: "year"` and `from` one year before the analysis date. Sum `commitsActivity` over the series into `commits12m`; an empty series is 0.

**6. Fetch the alerts.** Call `list_code_health_alerts`. Count the files across all alerts into `alerts`. If the call returns an error, set `alerts` to `null`: unavailable, not zero. If it is unavailable for every project, add a note saying so.

**7. Render.** Build a `ReportData` object that validates against the schema: `scope` (`name` and `source`), `analysisDate` (today, YYYY-MM-DD), `projectCount`, `projects` and `notes`. Copy the renderer to the user's output location as `{{portfolio-slug}}-portfolio-overview.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the chart appears instead of an error box.

**8. Record specifics.** Create or update the portfolio notes from the template.

## How the renderer reads the data

- **Score:** hotspot Code Health; average Code Health for a project without active hotspots, flagged *No active hotspots*.
- **Flags:** *Declining* and *Improving* when the score moved 0.1 or more over twelve months; uplift targets; hotspots below 9.0 (`hotspots` minus `healthyHotspots`); off-boarding risks; alerts; *Dormant* when `staleness` is dormant or there were no commits in twelve months.
- **Where your attention is needed:** every project below 9.0, calls to action first, then by the number of warning flags, then by commits. Each card gives the score, the distance to 9.5, the flags and a next step that points to the deeper report: *Refactoring targets* for uplift targets, *Architectural hotspots* for unhealthy hotspots without targets, *Key person risk* for off-boarding risks. A dormant project gets the choice to invest or retire it.
- **Watch list:** healthy and AI-optimal projects with at least one warning flag.
- **What works well:** healthy and AI-optimal projects, AI-optimal first, with how far each healthy one is from 9.5.
- **Summary tiles:** projects with data, the count per tier, and the share of all lines of code that sits in AI-optimal projects.

## Rules learned the hard way

- **No hotspots is not unhealthy.** A dormant project can report hotspot Code Health 0 with no classification. Map it to `null`; the renderer then uses the average.
- **Unavailable is not zero.** When a call fails for a project, keep the project with `available: false`, or the field `null`, and say so in the report. Never treat missing data as a good or bad score.
- **Don't let flags override the tier.** The user's tiers are by hotspot Code Health alone. A declining project at 9.6 is still AI-optimal; it goes on the watch list.
- **Small or dormant projects can rank high.** A tiny test repository with one unhealthy file lands in *Needs attention*. Keep it, but its card says it is dormant, so the reader can decide. Use the name filter for experiments the user doesn't want in the report.
- Use CodeScene's theme colours, as in the other reports. The tiers add a fourth colour, the brand teal, for AI-optimal.

## Troubleshooting

- **Every project lacks data:** the analyses may predate the packaged results. Tell the user to re-run the analyses, and stop.
- **Many projects:** lower the maximum, or use the name filter, to keep the number of calls manageable.
- **MCP tools missing after the user re-enables the server:** ask the user to send a new message, then search again.
