---
name: codescene-architectural-hotspots
description: Builds an architectural debt report for a CodeScene project, where each architectural component is placed in a Gartner PAID quadrant by change activity and Code Health, with trends, an Address-first table, estimated engineering outcomes and team ROI. Uses the CodeScene MCP server. Use when the user asks for architectural hotspots, architectural debt, or which components to uplift first.
disable-model-invocation: true
---

# Architectural hotspots report

Produces a one-page report: a bubble chart of components (X = commits, Y = average Code Health, size = lines of code) split into PAID quadrants, trend lines per component, the components to address first, the estimated outcomes of uplifting them to the target, and what that means in hours for a team.

The report data has one shape, defined in [report-data.schema.json](report-data.schema.json). The renderers listed under [Renderers](#renderers) turn it into a report; each has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project | required: its name or its id. Resolve a name to the id with `list_projects`; if several projects match, ask the user which one |
| Display name for the title | the project name from `list_projects` |
| Target Code Health for Address components | 10.0 |
| Team for ROI: developers, hours per week, weeks per year | 10, 40, 46 |
| Components to leave out | none |
| Renderer | the one that fits the client; see [Renderers](#renderers) |

## Data rules

- Leave out components whose `averageCodeHealth` is null, or whose value is 0 with a null `classification`; they have no files with Code Health.
- A `hotspotCodeHealth` of 0 with a null `classification` means the component has no hotspot data. Map it to `null`, not 0.
- Files that match no component (the unmapped-files summary) are not a component. Don't plot them. Mention them to the user only if they hold a large share of the files.

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch the components
- [ ] 3. Optionally find the worst file per component
- [ ] 4. Classify components into quadrants
- [ ] 5. Estimate outcomes for the Address components
- [ ] 6. Fill the report data and render the report
- [ ] 7. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tools `explore_project_components`, `explore_project_files` and `estimate_engineering_outcomes`. The server's namespace prefix varies between clients. If they are missing, ask the user to connect and authorize the CodeScene MCP server, and stop.

**2. Fetch the components.** Call `explore_project_components` with `page_size: 1000`, following `nextPageToken` until it is absent. Map each component to `ComponentData`:

| `ComponentData` | Component field |
|---|---|
| `name` | `name` |
| `health` | `averageCodeHealth.value` |
| `hotspotHealth` | `hotspotCodeHealth.value`, or `null` |
| `trend` | `averageCodeHealth.trend`, omitted when absent |
| `changes` | `changeFrequency` (a commit touching several files counts once) |
| `linesOfCode` | `linesOfCode` |
| `files` | `fileCount` |
| `hotspots` | `hotspots` |
| `upliftTargets` | `upliftTargets` |

Keep `knowledge` (main author, `isActive`, `formerContributorShare`) for the conversation; the report doesn't show it yet.

**3. Worst file (optional).** For each plotted component, call `explore_project_files` with `component` set to its name and `sort: "codeHealth.value:asc"`, `page_size: 1`. Use the file name (the last segment of `path`) and its `codeHealth.value`, rounded to two decimals, as `worstFile`. The calls are independent; run them in parallel. If a component returns `pending_reanalysis`, omit `worstFile`; the renderer shows a dash.

**4. Classify.** The renderer does this; know the rules to explain them. Healthy means `health >= 9.0`. Active means `changes >` the mean commits across the plotted components: the first split of the head/tail breaks algorithm. Change activity follows a power law, so the median would mark half the components as active however little most of them change; the mean separates the busy head, which carries most commits, from the long quiet tail. Address = active and unhealthy, Plan = active and healthy, Delay = quiet and unhealthy, Ignore = quiet and healthy.

**5. `estimate_engineering_outcomes`.** Call it for:
- each Address component, with `baseline` = its `health` and `target` = the target;
- the whole codebase, with `baseline` = the lines-of-code-weighted average `health` of the plotted components, and `target` = the same average with the Address components set to the target.

Put the whole codebase first in `outcomes`; renderers highlight the first entry and show the midpoint of each 90% interval. If there are no Address components, leave `outcomes` empty and both outcome sections disappear.

**6. Render.** Build a `ReportData` object from steps 2–5 that validates against the schema. Copy the chosen renderer to the user's output location as `{{project-slug}}-architectural-hotspots.<ext>`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged.

**7. Record specifics.** Create or update the project notes from the template: inputs, left-out components, decisions and observations.

## Renderers

[renderers/report.html](renderers/report.html) is a single self-contained HTML file: inline SVG, plain JavaScript, no libraries and no network access. It works in any client that can write a file, and opens in any browser. Print it to PDF for email.

The `{{REPORT_DATA}}` block is a `<script type="application/json">` element. Put only JSON there: no comments, no trailing commas. Names are escaped by the renderer, so paste them as they are. After writing, open the file in a browser, or a preview the client offers, and check that the chart appears instead of an error box.

## How the renderer reads the data

- ROI hours: a productivity gain p means the same work takes 1/(1 + p) of the time, using the midpoint estimate. A component's share of the team's time is approximated by its share of commits. The caption states these assumptions.
- Trend lines: drawn left of a bubble, sloping up for improving and down for declining, steeper when `pace` is `fast`. Steady components and components without a trend get no line.

## Chart rules learned the hard way

- SVG `<title>` tooltips don't show in every viewer. The renderer uses an absolutely positioned card; keep `pointer-events="none"` on labels and overlays so they don't steal the hover.
- Address components are orange diamonds with a soft ring; everything else is a circle coloured by Code Health. Don't go back to plain dots for Address.
- The Y axis always reaches at least 1.0 below Healthy, so the Address and Delay areas are visible even when every component is healthy. An empty Address area says "Nothing to address".
- Bubbles that would overlap within the same quadrant are merged into a numbered group, positioned and sized by its members' lines of code. Groups never span quadrants. Hovering a group lists its members, worst Code Health first; clicking spreads them out around it and dims the rest. Nothing to configure: the tables still list every component.
- Label placement avoids bubbles and trend lines. When you add marks to the chart, add them to the obstacles in `placeLabels`. In a dense cluster, a label that fits nowhere is left off (Address components are always labelled); the hover card still names it.
- With up to three Address components, outcomes and ROI show one card per component. With more, the renderer shows the whole-codebase outcome and ROI as two cards, followed by one table row per component; one card each doesn't scale. Keep the whole codebase first in `outcomes` either way.
- Keep narrow side columns out of tables: put tables full width, and let long names wrap instead of truncating.
- Use CodeScene's theme colours (the CSS variables in `:root`) and its three Code Health classes: unhealthy (red) below 4.0, problematic (yellow) below 9.0, healthy (teal) from 9.0. Bubbles use the pastel fills; numbers and labels use the darker `-ink` variants so they stay readable on white. Address components are diamonds in the theme red with a navy outline, set in a white halo, so they stand out from the red-tinted Address area; their Code Health shows on the Y axis, in the hover card and in the tables. Dark mode follows the viewer's system setting.

## Troubleshooting

- **No components returned:** the project has no architectural components configured, or the latest analysis predates them. Ask the user to configure components and re-run the analysis.
- **`pending_reanalysis` for a component:** its results are available after the next analysis. Continue without its worst file.
- **MCP tools missing after the user re-enables the server:** ask the user to send a new message, then search again.
