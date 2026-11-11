---
name: codescene-new-code-insights
description: Builds a report on whether the code added to a CodeScene project over the last month is healthy and AI-ready. It shows how much new code there is, its median and lowest Code Health per module and package, an alert for new technical debt, the share that is AI-optimal, and which developers to involve. Uses the CodeScene MCP server. Use when the user asks about new code, code added recently, whether new code is healthy or AI-ready, whether new technical debt is being added, or who is writing the new code.
disable-model-invocation: true
---

# New code insights report

Produces a one-page report on the files added to one project since CodeScene's Code Health snapshot a month before the latest analysis. For each module and package it shows the files and lines added, the share that is test code, and the **median** and **lowest** Code Health of the new files. It answers two questions a leader has about the code being added now:

- **Is it adding technical debt?** New code is where debt is cheapest to prevent. A new file below the alert threshold, 9.0 by default, is an **alert**.
- **Is it AI-ready?** Code at 9.5 or more by default is **AI-optimal**: where AI assistants and people both work at their best. The report shows the share of new lines that is.

The developer columns show where new knowledge sits and who to involve. They are not a productivity measure; say so if the user reads them that way.

The data comes from `explore_project_files`: the latest analysis, not live data.

The report lists developers by name. Never show email addresses or account ids.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}-new-code-insights.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project | required: its name or its id. Resolve a name to the id with `list_projects`; if several projects match, ask the user which one |
| Display name for the title | the project name from `list_projects` |
| Alert threshold | `9.0` |
| AI-optimal from | `9.5` |
| Line coverage target | `0.8`, used only when the project has coverage data |
| Rows in the package, developer and lowest-file tables | `20` each; `0` shows all |
| Packages | from the project notes: how modules and packages are read from the paths |
| Author names | from the project notes: aliases to merge |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch every file
- [ ] 3. Find the new files
- [ ] 4. Group them into modules and packages
- [ ] 5. Merge author aliases
- [ ] 6. Fill the report data and render the report
- [ ] 7. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tool `explore_project_files`. The server's namespace prefix varies between clients. If it is missing, ask the user to connect and authorize the CodeScene MCP server, and stop.

**2. Fetch every file.** Call `explore_project_files` with the project id and `page_size` 1000. While the result has a `nextPageToken`, call again with it as `page_token`, until every page is read. Check that the number of files read equals `summary.totalFiles`. A large project returns more than fits in your context: save each page to a file and process them with a script, not by reading them.

**3. Find the new files.** Each file's `codeHealth.series` has a Code Health point for each snapshot: the latest analysis, a month before it and a year before it, when the file existed then. A file is **new** when it has a point at the latest date but none at the month-ago date. Take the month-ago date from the files that have one; it is the same for every file. Set `range.from` to that date and `range.to` and `analysisDate` to the latest one.

Map each new file to a `File`:

| `File` | Field |
|---|---|
| `path`, `language`, `lines` | `path`, `language`, `linesOfCode` |
| `codeHealth` | `codeHealth.value` |
| `coverage` | `coverage.lineCoverage`, or null when it is missing or null |
| `mainAuthor`, `mainAuthorShare`, `authorCount` | `knowledge.mainAuthor.name`, `knowledge.mainAuthor.ownership`, `knowledge.authorCount`; the name after step 5 |
| `lastModified` | `lastModified.date` |
| `test` | true when the path is test code: a `test`, `tests`, `__test__` or `__tests__` folder, or a name such as `*.test.*`, `*.spec.*` or `*_test.*`. Use the patterns in the project notes when they differ |
| `module`, `package` | from step 4 |

**4. Group into modules and packages.** A **module** is the top-level part of the system, usually the first folder below the repository. A **package** is the folder that holds a feature, with its source and tests grouped together. Build it from the path inside the module: drop source and test roots such as `src`, `test`, `tests`, `__test__`, `__tests__` and `packages`, drop leading folders that only repeat the module or the language's root namespace, then keep the first two folders left and prefix the module. For example, `web/src/components/charts/bar.tsx` and `web/src/components/charts/__test__/bar.test.tsx` both belong to `web/components/charts`. Show the user the largest packages and ask whether the grouping fits before rendering. Record the rule in the project notes.

**5. Merge author aliases.** The same person can appear under several names, such as a display name and a login. Use the aliases in the project notes. Otherwise, list names that look like the same person and ask the user which to merge; don't guess.

**6. Render.** Build a `ReportData` object that validates against the schema, with `project` (`name`, `source`, `id`), `generatedAt`, `threshold`, `aiOptimal`, `coverageTarget`, `maxPackages`, `maxDevelopers`, `maxLowestFiles` and `notes`. Copy the renderer to the user's output location as `{{project-slug}}-new-code-insights.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the tables appear instead of an error box.

Use `notes` for facts the reader needs, for example which author names were merged, or a main author known only by a login.

**7. Record specifics.** Create or update the project notes from the template, including the package rule and the alias merges, so the next run uses them.

## How the renderer reads the data

- **Header:** "Is new code healthy and AI-ready?", with the number of new files and the date range.
- **Summary:** new files, lines of new code and the share that is test code, the median and lowest Code Health, the share of new lines that is AI-optimal, and line coverage when there is any. A banner turns into an alert when any new file is below the threshold.
- **By module and by package:** sortable tables with files, lines, test share, the Code Health range on the 1–10 scale with the AI-optimal line marked, the median, the lowest, the share of lines that is AI-optimal, and the main authors with their share of the lines. Rows with a file below the threshold are highlighted. The package table shows at most `maxPackages` rows, by the sorted column, and has a filter that searches every package and author.
- **Developer contributions:** each developer's files and lines as main author, the median and lowest Code Health, their lines below AI-optimal, the share that is AI-optimal, their coverage, and their main packages. Rows with code below AI-optimal are highlighted in amber, and rows with code below the threshold in red. At most `maxDevelopers` rows, with a filter.
- **Lowest Code Health:** only new files below 10, lowest first, at most `maxLowestFiles` of them.
- **Coverage, when present:** a line coverage tile, a Coverage column with the share of production lines measured, and the least covered new production files below the target. Coverage is weighted by lines and covers production code only. Without any coverage data, these are left out and the notes say coverage is not integrated.

## Rules learned the hard way

- **Read every page.** A report built from the first page of files undercounts.
- **New means new to the analysis.** A file renamed or moved during the month also counts as new, and deleted files are not visible. Say so in `notes` when a large share of the new files may be moves.
- **Coverage is optional.** It comes from CodeScene's coverage integration, which many projects don't have, and some languages are never measured. Keep a missing value null, never 0, and always show how much of the code is measured next to a coverage figure.
- **One main author per file.** A file counts for the developer who wrote most of it; a package's main authors are weighted by the lines of the files they lead.
- **Never show email addresses.** Map author names only, and merge aliases into a display name.
- Use CodeScene's theme colours, as in the other reports.

## Troubleshooting

- **No new files:** nothing was added since the month-ago snapshot, or the project was first analysed less than a month ago and has no month-ago point. Check whether any file has a month-ago point before saying the project has no new code.
