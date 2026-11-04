---
name: codescene-refactoring-targets
description: Turns CodeScene's uplift targets into a prioritized refactoring backlog for an engineering manager. For each target it shows why it was picked, where in the file to start, who to involve, what to watch out for, and the estimated outcome of the refactoring. Primary and secondary targets also get a refactoring spec the manager can hand to a coding agent. Uses the CodeScene MCP server. Use when the user asks what to refactor first, how to act on uplift targets, or for a refactoring plan or backlog.
disable-model-invocation: true
---

# Refactoring targets report

Produces a one-page report that an engineering manager can plan from: a ranked backlog of CodeScene's uplift targets, one card per target with the evidence behind it, the functions to start with, the people to involve and the risks to plan for, plus the estimated outcome of refactoring each one. Each primary and secondary target also has a **refactoring spec**: a Markdown brief, built by the renderer from the report data, that the manager copies or downloads and gives to a coding agent.

Uplift targets are files CodeScene recommends refactoring: unhealthy code that the team changes often, so improving it pays back in day-to-day delivery. CodeScene marks them at two levels. **Primary** and **secondary** targets are the best candidates in the whole project. **Local** targets are the best candidates within their own architectural component, and come next.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}-refactoring.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project | required: its name or its id. Resolve a name to the id with `list_projects`; if several projects match, ask the user which one |
| Display name for the title | the project name from `list_projects` |
| Target Code Health after refactoring | 9.0 (healthy) |
| Maximum number of targets in the report | 10 |
| Include local targets | yes |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch the uplift targets
- [ ] 3. Rank and cut the list
- [ ] 4. Get the prioritized refactorings and reviews
- [ ] 5. Estimate outcomes
- [ ] 6. Fill the report data and render the report
- [ ] 7. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tools `explore_project_files`, `list_prioritized_refactorings`, `review_analyzed_file` and `estimate_engineering_outcomes`. The server's namespace prefix varies between clients. If they are missing, ask the user to connect and authorize the CodeScene MCP server, and stop.

**2. Fetch the uplift targets.** Call `explore_project_files` with `sort: "upliftTarget.type:asc"` and `page_size: 50`. That lists local, primary and secondary targets before all other files. Follow `nextPageToken` until a page contains a file without `upliftTarget.type`; stop there. A file is a target when `upliftTarget.isTarget` is true (primary or secondary) or `upliftTarget.type` is `"local"`. The results are large because of the coupling data; read them with a JSON tool rather than in full.

If there are no targets, tell the user and render the report anyway; it says so.

**3. Rank and cut.** Order primary, then secondary, then local; within each type, most commits (`changeFrequency`) first. Leave out local targets if the user said so. Keep the first *maximum number* and tell the user how many were left out.

Map each kept file to a `Target`:

| `Target` | File field |
|---|---|
| `path` | `path` |
| `component` | `component`, or `null` |
| `type` | `upliftTarget.type` |
| `health` | `codeHealth.value`, rounded to two decimals |
| `healthSeries` | `codeHealth.series`, as `{ date, value }` with values rounded to two decimals |
| `trend` | `codeHealth.trend`, omitted when absent |
| `changes` | `changeFrequency` |
| `linesOfCode` | `linesOfCode` |
| `coverage` | `coverage.lineCoverage`, or `null` |
| `isHotspot` | `isHotspot` |
| `owner` | `knowledge.mainAuthor` as `{ name, ownership, isActive }`, or `null` |
| `formerContributorShare` | `knowledge.formerContributorShare`, or `null` |
| `offboardingRisk` | `offboardingRisk.isRisk` |
| `coupledFiles` | the first three of `coupling`, as `{ path, couplingPercent }` |

**4. Get the prioritized refactorings and reviews.**

*Prioritized refactorings, for every kept target.* Call `list_prioritized_refactorings` once with `file_paths` = the paths of the kept targets (up to 25 per call). For each file with `recommendations`, map them in rank order to `startHere`: `{ target, scope, recommendationType, text, loc, cyclomaticComplexity, revisions, defects, issues }`, taking the numbers from `evidence` and `issues` from `evidence.codeHealthIssues`. A file returned with a `status` instead, such as `not_uplift_target`, gets no `startHere`; put its `message` in `startHereMessage`.

*File reviews, for primary and secondary targets.* Call `review_analyzed_file` for each; the calls are independent, so run them in parallel. Map the review's `findings` whose `severity` is not `"improvement"` to `findings`, as `{ name, severity, recommendation, location }`, where `location` is `{ symbol, startLine, endLine }` when present. Keep the server's severity text and recommendation as they are. The review adds line ranges and CodeScene's guidance per Code Health issue to the refactoring spec.

If a review fails, put the error message in `reviewError` and continue; the target keeps its `startHere` from the prioritized refactorings. Tell the user which reviews failed. Never fill `findings` or `startHere` from anywhere else.

**5. `estimate_engineering_outcomes`.** For each target whose `health` is below the target Code Health, call it with `baseline` = `health` and `target` = the target Code Health. Targets with the same rounded `health` share one call. Store `defects`, `developmentTime` and `combinedProductivityImpact` as `outcome.defects`, `outcome.developmentTime` and `outcome.productivity`.

**6. Render.** Build a `ReportData` object that validates against the schema: `project` (with `id`, the CodeScene project id), `analysisDate` (the `asOf` date of the results, as YYYY-MM-DD), `targetHealth`, `targets` in rank order, and `omitted` = the number of targets left out in step 3. Copy the renderer to the user's output location as `{{project-slug}}-refactoring-targets.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there: no comments, no trailing commas. Open the file in a browser, or a preview the client offers, and check that the backlog appears instead of an error box.

**7. Record specifics.** Create or update the project notes from the template: inputs, left-out targets, failed reviews and observations.

## How the renderer reads the data

- **Backlog table:** one row per target in rank order, so the manager can read the plan at a glance.
- **Target cards:** the evidence for each target. Risk badges come from the data: *Declining* when the trend is declining, *Knowledge risk* when `offboardingRisk` is true or the main author is inactive, and *Needs tests first* when line coverage is below 50% or unknown: add tests around the code before refactoring it. The summary counts each of these as "N of M targets".
- **Who to involve:** the targets grouped by main author, with whether the author is still active.
- **Refactoring specs:** primary and secondary targets have a *Refactoring spec* button, in the backlog and on their card. It opens the spec with *Copy* and *Download .md* buttons. The spec is filled in from the report data: the goal, the functions to refactor in CodeScene's order with their evidence, the remaining Code Health issues with CodeScene's guidance, what to check first (tests, co-changing files, the main author), constraints, how the agent should work with the CodeScene tools, and when it is done. No model runs in the report; the coding agent does the reasoning, in the repository, when the manager hands it the spec.
- **Outcomes** show the midpoint of each 90% interval from the outcome model, for development inside that file.

## Rules learned the hard way

- Don't rank by Code Health alone. CodeScene's uplift targets already combine Code Health with change activity; keep its type order and use commits within a type.
- Take `startHere` from `list_prioritized_refactorings`, not from the file review: one call covers every target, and it keeps working when a review fails.
- `review_analyzed_file` can fail on large, unhealthy files when the server returns findings that don't match its own output schema. That is a server issue: report it, keep the target in the backlog, and let the spec say the per-issue guidance is missing.
- Keep paths readable: the renderer shows the file name prominently and the full path below it, and lets long paths wrap instead of truncating.
- Use CodeScene's theme colours and its three Code Health classes, as in the other reports: unhealthy (red) below 4.0, problematic (yellow) below 9.0, healthy (teal) from 9.0.

## Troubleshooting

- **No targets:** the project has no uplift targets in its latest analysis. That usually means no unhealthy code is changed often; the report says so.
- **MCP tools missing after the user re-enables the server:** ask the user to send a new message, then search again.
