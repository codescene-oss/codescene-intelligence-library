---
name: codescene-contributor-spotlight
description: Builds a report on what one contributor built in a CodeScene project over the past year. It shows the new files they are main author of, how healthy, AI-optimal and well-tested that code is, how they compare with the rest of the team on Code Health, coverage and volume, their recent pull requests and Code Health MCP use, and the knowledge they hold or leave behind. Uses the CodeScene MCP server. Use when the user asks what a person contributed, for a contributor's year in review, or how a developer's code compares with the team's.
disable-model-invocation: true
---

# Contributor spotlight

Produces a one-page report on one person's contribution to one project over the past year:

- **What they built:** the files they are main author of that are new within the year, by area, with the files they put the most lines into.
- **How healthy it is:** median and lowest Code Health, the share of lines that is AI-optimal, the share that is test code, and line coverage when the project has it.
- **How they compare:** their median Code Health, coverage and lines of new code against every developer with enough new code, shown as unnamed dots.
- **Pull requests and the local safeguard:** their recent pull requests and what CodeScene's review found, and their Code Health MCP safeguard checks, with a one-line verdict.
- **The knowledge they hold:** every file they are main author of, how much of it only they have touched, and who else knows it. For a former contributor, the knowledge they leave.

The report celebrates and explains a contribution. It is not a performance review: lines of code are not productivity, and the benchmark names nobody but the contributor. Say so if the user reads it that way, and ask before making a report about someone for a third party.

The data comes from `explore_project_files`, the latest analysis, plus `get_pull_request_safeguard_outcomes` and `get_mcp_safeguard_insights` when they have data.

The report shows people by name only. Never show email addresses or account ids, even where a tool returns them as labels.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}-contributor-spotlight.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project | required: its name or its id. Resolve a name to the id with `list_projects`; if several projects match, ask the user which one |
| Contributor | required: a name as it appears in CodeScene. If several authors match, such as two people with the same first name, ask the user which one |
| Minimum new files for the benchmark | `10`: developers with fewer new files are left out of the comparison |
| AI-optimal from | `9.5` |
| Stable band | `0.05`: a pull request's Code Health change smaller than this counts as maintained |
| Author names | from the project notes: aliases to merge and bots |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch every file
- [ ] 3. Find the contributor's new files
- [ ] 4. Build the knowledge summary and the team benchmark
- [ ] 5. Add pull requests and MCP use, when there is data
- [ ] 6. Fill the report data and render the report
- [ ] 7. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tool `explore_project_files`. The server's namespace prefix varies between clients. If it is missing, ask the user to connect and authorize the CodeScene MCP server, and stop.

**2. Fetch every file.** Call `explore_project_files` with the project id and `page_size` 1000. While the result has a `nextPageToken`, call again with it as `page_token`, until every page is read. Check that the number of files read equals `summary.totalFiles`. A large project returns more than fits in your context: save each page to a file and process them with a script, not by reading them.

**3. Find the new files.** Merge author aliases first: the same person can appear under several names, such as a display name and a login. Use the aliases in the project notes; otherwise list names that look like the same person and ask the user which to merge.

Each file's `codeHealth.series` has a point for the latest analysis, a month before it and a year before it, when the file existed then. A file is **new** when it has no point at the year-ago date. Take that date from the files that have one; it is the same for every file. Set `range.from` to it and `range.to` to the latest date. The contributor's new files are the new files whose `knowledge.mainAuthor.name`, after merging aliases, is the contributor.

Map each one to a `File`:

| `File` | Field |
|---|---|
| `path`, `language`, `lines` | `path`, `language`, `linesOfCode` |
| `linesAdded` | `knowledge.mainAuthor.linesAdded` |
| `codeHealth` | `codeHealth.value` |
| `coverage` | `coverage.lineCoverage`, or null when it is missing or null |
| `changes`, `hotspot` | `changeFrequency`, `isHotspot` |
| `test` | true when the path is test code: a `test`, `tests`, `__test__` or `__tests__` folder, or a name such as `*.test.*`, `*.spec.*`, `*_test.*` or `*Test.java`. Use the patterns in the project notes when they differ |
| `area` | the folder that holds the feature: drop the repository folder, source and test roots such as `src` and `test`, and folders that only repeat the module or the language's root namespace, then keep the first three folders left. Source and tests of a feature land in the same area |

Set `contributor.name` to the display name, `contributor.shortName` to how the text should refer to them (usually the first name), and `contributor.active` to `knowledge.mainAuthor.isActive`. For a former contributor, set `lastSoloChange` to the latest `lastModified.date` among the files where they are the only author.

If the contributor has no new files, say so to the user; the report says the same.

**4. Knowledge and benchmark.** For `knowledge`, use every file the contributor is main author of, of any age: the count and lines, how many have `knowledge.mainAuthor.ownership` of at least 0.9 (`mostlyOwned`), how many have `knowledge.authorCount` 1 (`solo`), the paths of those that are hotspots, and the other names among their `knowledge.contributors`, most files first, aliases merged and bots left out.

For `team.developers`, group every new file by main author, aliases merged and bots left out, and keep the authors with at least the minimum number of new files. For each, give `files`, `lines`, the median and the line-weighted average of `codeHealth.value`, and line coverage of the production files, weighted by lines, or null. Mark the contributor with `self: true`. Don't put names in `team`: the benchmark shows everyone else as an unnamed dot. Keep everyone, current and former contributors.

**5. Pull requests and MCP use.** Both are optional; leave `pullRequests` or `mcp` out when there is no data.

- Call `get_pull_request_safeguard_outcomes` with the project id, `from` a year before today and `page_size` 1000, and read every page. The data usually reaches back only a few weeks; set `pullRequests.range.from` to the earliest pull request date and say so in `notes`. Map each pull request with the contributor among its `authors` to a `PullRequest`: `prId`, `analysisDate` as YYYY-MM-DD, `size` as `files` when present, the four `statistics` counts, and `codeHealth.change` as `codeHealthChange` when present. Set `teamPullRequests` to the pull requests by people, leaving out those whose only authors are bots, and `teamWithFindings` to those of them with findings.
- Call `get_mcp_safeguard_insights` with the project id. Find the contributor in `selectedPeriod.checksPerDeveloper.topDevelopers` by `name`, aliases merged, for `checks`, and in `previousPeriod` for `previousChecks`; use 0 and null when they are not listed. Take `teamMedian` from `selectedPeriod.checksPerDeveloper.median`, and `activeUsers`, `teamChecks`, `prevented` and `uplifts` from `selectedPeriod.summary`. Match by `name` only: the `label` can be an email address and never goes in the report. Compare names after Unicode normalization (NFC): the same name can be stored with a precomposed or a combining accent.

**6. Render.** Build a `ReportData` object that validates against the schema, with `project` (`name`, `source`, `id`), `generatedAt`, `aiOptimal`, `stableBand` and `notes`. Copy the renderer to the user's output location as `{{project-slug}}-{{contributor-slug}}-spotlight.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the sections appear instead of an error box.

Use `notes` for facts the reader needs, for example which author names were merged, or how far back the pull request data reaches.

**7. Record specifics.** Create or update the project notes from the template, including the alias merges, bots and area rule, so the next run uses them.

## How the renderer reads the data

- **The short version:** new files and lines, median and lowest Code Health, the AI-optimal share, test code and coverage, and the three largest areas.
- **How they compare:** a row per metric with the contributor's value, rank and the team median, over a strip of dots. Medians of new code are often all 10, so the Code Health strip plots the line-weighted average to separate developers. Lines of new code use a log scale.
- **Pull requests and the local safeguard:** pull requests with findings against the team's share, how many maintained Code Health within the stable band, files per pull request, pull requests per week, and MCP checks against the 30 days before. The **verdict** picks one line from the data: findings merged anyway, no findings, findings fixed, or no MCP use.
- **What they built:** areas by lines, with tests, median and lowest Code Health, AI-optimal share and coverage. Areas with fewer than four files fold into one row.
- **Signature files:** the 12 new files with the most lines added.
- **New files below AI-optimal** and **the knowledge they hold**, or leave for a former contributor.

## Rules learned the hard way

- **Never show email addresses.** The MCP insights label some developers by email; use the display name only.
- **Read every page.** A contributor's new files are spread across all of them.
- **This is the analysis snapshot.** The analysis has no commit dates per author: changes to older files and deleted files aren't counted, and renamed or moved files count as new. Say so in the report, as the renderer does.
- **Don't name the team in the benchmark.** It compares one person with unnamed peers; naming them turns it into a ranking.
- **Ask which person.** First names repeat; never pick one silently.
- Use CodeScene's theme colours, as in the other reports.

## Troubleshooting

- **The contributor is not found:** list the main authors whose names contain what the user typed, and ask.
- **No pull requests or MCP data:** leave those parts out; the section disappears.
- **Every benchmark dot sits at 10:** expected in a healthy project; the median row says every developer is at 10, and the average separates them.
