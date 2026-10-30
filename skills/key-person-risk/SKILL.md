---
name: codescene-key-person-risk
description: Builds a key person risk report for a CodeScene project, in truck factor terms. It gives the project's truck factor, shows what knowledge would leave with each key person, highlights CodeScene's off-boarding risks, and covers the uplift targets that depend on one person, the components led by one person, and the knowledge already lost. Uses the CodeScene MCP server. Use when the user asks about key person dependencies, truck factor, bus factor, knowledge risk, off-boarding risk, or who knows which code.
disable-model-invocation: true
---

# Key person risk report

Produces a one-page report on key person dependencies, in the language of the **truck factor**: the smallest number of people who could leave before a large part of the code has no one who knows it.

Knowledge concentrated in one person is a risk when the code is also hard to learn (low Code Health), unsafe to change (low coverage) and needed often (frequent change). The report therefore stays with the code that matters:

- **CodeScene's off-boarding risks:** files where little knowledge would remain if their two main contributors left. They are the headline of the report.
- **CodeScene's uplift targets:** unhealthy, frequently changed files. Those that depend on one person are the next priority.
- **Architectural components** for the project's truck factor and a compact component view.

The report names people. It is about where knowledge sits and how fragile that code is; keep the wording factual. It states the Code Health and coverage of the code each person mainly knows, and how that Code Health changed over the last year, and leaves the interpretation to the reader.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}-key-person-risk.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project id | required; find it with `list_projects` |
| Display name for the title | the project name from `list_projects` |
| Concentration threshold: main author's share of the code | 50% |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch the components
- [ ] 3. Fetch the uplift targets
- [ ] 4. Fetch the off-boarding risks
- [ ] 5. Fill the report data and render the report
- [ ] 6. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tools `explore_project_components` and `explore_project_files`. The server's namespace prefix varies between clients. If they are missing, ask the user to connect and authorize the CodeScene MCP server, and stop.

**2. Fetch the components.** Call `explore_project_components` with `page_size: 1000` and `sort: "changeFrequency:desc"`. Map each component with an `averageCodeHealth` above 0 to a `Component`:

| `Component` | Component field |
|---|---|
| `name` | `name` |
| `owner` | `knowledge.mainAuthor` as `{ name, ownership, isActive }` |
| `authorCount` | `knowledge.authorCount` |
| `formerContributorShare` | `knowledge.formerContributorShare` |
| `health` | `averageCodeHealth.value` |
| `trend` | `averageCodeHealth.trend`, omitted when absent |
| `changes` | `changeFrequency` |
| `linesOfCode` | `linesOfCode` |
| `offboardingRisks` | `offboardingRisks` |
| `upliftTargets` | `upliftTargets` |

**3. Fetch the uplift targets.** Call `explore_project_files` with `sort: "upliftTarget.type:asc"` and `page_size: 50`, following `nextPageToken` until a page has a file without `upliftTarget.type`. A file is a target when `upliftTarget.isTarget` is true (primary or secondary) or `upliftTarget.type` is `"local"`. The results are large because of the coupling data; read them with a JSON tool.

**4. Fetch the off-boarding risks.** Call `explore_project_files` with `sort: "offboardingRisk.isRisk:desc"`, paging until a file has `isRisk` false. The summary's `offboardingRiskCount` tells you how many to expect.

Map the union of steps 3 and 4 to `File`s, one per path:

| `File` | File field |
|---|---|
| `path` | `path` |
| `component` | `component`, or `null` |
| `type` | `upliftTarget.type` for uplift targets; `null` otherwise |
| `health` | `codeHealth.value`, rounded to two decimals |
| `healthYearAgo` | the first value of `codeHealth.series`, rounded, when its date is at least 300 days before the last one; otherwise `null` |
| `changes` | `changeFrequency` |
| `linesOfCode` | `linesOfCode` |
| `coverage` | `coverage.lineCoverage`, or `null` |
| `owner` | `knowledge.mainAuthor` as `{ name, ownership, isActive }` |
| `contributors` | `knowledge.contributors` as `{ name, ownership, isActive }`, in the order given |
| `formerContributorShare` | `knowledge.formerContributorShare`, or `0` |
| `offboardingRisk` | `offboardingRisk.isRisk` |
| `remainingKnowledge` | `offboardingRisk.remainingKnowledge`, or `null` |

**5. Render.** Build a `ReportData` object that validates against the schema: `project` (with `id`), `analysisDate` (the results' `asOf`, as YYYY-MM-DD), `concentration` (the threshold as a fraction), `components`, `files` and `notes`. Copy the renderer to the user's output location as `{{project-slug}}-key-person-risk.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the chart appears instead of an error box.

Use `notes` for facts the reader needs, for example author aliases (see below).

**6. Record specifics.** Create or update the project notes from the template.

## How the renderer reads the data

- **Truck factor of a file:** *1* when its main author wrote 50% or more of it (the threshold): the knowledge leaves with them. *2* when CodeScene flags it as an off-boarding risk and no one holds half: little knowledge remains if its two main contributors leave.
- **Truck factor of the project:** an estimate from main-author data. Components whose main author is already inactive count as lost from the start. Then remove the active person who leads the most actively changed components, then the next, until components carrying more than half of all commits are without their main author. The number of people removed is the truck factor; 0 means more than half is already lost. The report names them and says it is an estimate.
- **What leaves with each person:** one row per person, one block per file they are the main author of, sized by commits. Off-boarding risks are red and labelled with how much knowledge would remain; other truck factor 1 files are grey.
- **Off-boarding risks:** one card each, with the two people who hold the knowledge, how much would remain, Code Health now and a year ago, coverage, the next contributor to bring in, and an action.
- **People:** a sortable table: off-boarding risks, truck factor 1 files, their commits, the Code Health of that code now and a year ago (lines-of-code-weighted), coverage, and the components each person leads.
- **Components:** those led by one person or holding off-boarding risks.
- **Knowledge already lost:** components and files where former contributors wrote at least half of the code, or whose main author is inactive.

## Rules learned the hard way

- **Highlight only the off-boarding risks.** A chart that gives every file or component equal weight is noise. Off-boarding risks are the only saturated colour; everything else is muted.
- **Unknown coverage is not missing tests.** Many projects don't report coverage. Only measured coverage below 50% counts against a file; the report shows unknown coverage as unknown.
- **Author aliases split one person into several.** CodeScene counts each author name separately unless the project maps them, which also lowers the truck factor estimate's accuracy. If the same person appears under several names (for example a full name and a nickname), tell the user to configure author aliases in CodeScene and re-run the analysis, and add a note. Never merge names yourself.
- Use CodeScene's theme colours and its three Code Health classes, as in the other reports: unhealthy (red) below 4.0, problematic (yellow) below 9.0, healthy (teal) from 9.0.

## Troubleshooting

- **No off-boarding risks:** the chart still shows the truck factor 1 files; the risk section says none were found.
- **Nothing in "Knowledge already lost":** every main author is active and no code was written by former contributors. The section says so.
- **MCP tools missing after the user re-enables the server:** ask the user to send a new message, then search again.
