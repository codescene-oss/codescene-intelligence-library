---
name: codescene-change-coupling
description: Builds a change coupling report for software architects from a CodeScene project. It aggregates file-level change coupling into implicit dependencies between architectural components, shows the coordination each dependency forces between people, and uses Code Health to judge how hard each dependency will be to break. Uses the CodeScene MCP server. Use when the user asks about change coupling, temporal coupling, logical coupling, implicit or hidden dependencies, coordination costs, Conway's law, or how the architecture holds up in practice.
disable-model-invocation: true
---

# Architecture: Change coupling report

Produces a one-page report for software architects on the cost of change. Complexity comes in two shapes: code that is hard to understand on its own, which Code Health measures, and code that looks simple but behaves anything but because of its dependencies. Static dependency graphs list every dependency and miss the logical ones, such as services coupled through a message bus. Change coupling comes from developer behaviour instead: files that keep co-evolving in the same commits. The report lifts CodeScene's file-level change coupling to the architecture, separates the expected dependencies from the expensive ones, and combines both kinds of complexity:

- **Logical dependencies:** coupling between files in different architectural components, the places where change doesn't stay local.
- **Coordination:** code that logically belongs together but is maintained by different people, measured from each file's knowledge distribution. Conway's law, measured.
- **Difficulty:** the Code Health of the coupled files. Coupling between unhealthy files is expensive to untangle and needs refactoring before it can be pulled apart.

The skill only collects data; the renderer does the aggregation. The report data has one shape, defined in [report-data.schema.json](report-data.schema.json): the coupled files and the coupled pairs, as CodeScene reports them. [renderers/report.html](renderers/report.html) has a `{{REPORT_DATA}}` block that is the only part you fill in. Per-project inputs and decisions go in the user's workspace, not in this library, as `codescene/projects/{{project-slug}}-change-coupling.md`, created from [templates/project-notes.md](templates/project-notes.md).

Follow [../../shared/ground-rules.md](../../shared/ground-rules.md) throughout.

## Inputs

Collect these before starting. Use the project notes if they exist; otherwise ask the user.

| Input | Default |
|---|---|
| Project | required: its name or its id. Resolve a name to the id with `list_projects`; if several projects match, ask the user which one |
| Display name for the title | the project name from `list_projects` |
| Maximum number of files to scan | 1000 |

## Workflow

```
- [ ] 1. Check data access
- [ ] 2. Fetch the files with change coupling
- [ ] 3. Assess which coupling is a problem
- [ ] 4. Fill the report data and render the report
- [ ] 5. Record project specifics
```

**1. Check data access.** Find the CodeScene MCP tool `explore_project_files`. The server's namespace prefix varies between clients. If it is missing, ask the user to connect and authorize the CodeScene MCP server, and stop.

**2. Fetch the files with change coupling.** Call `explore_project_files` with `sort: "changeFrequency:desc"` and `page_size: 100`, following `nextPageToken`. Only files that change often have measured coupling, so stop after the first page in which no file has a non-empty `coupling`, or at the maximum number of files. The results are large; read them with a JSON tool rather than in full.

Each file's `coupling` lists its coupled partners as `{ path, couplingPercent, averageChangeFrequency, component }`. CodeScene reports every pair from both sides; keep each unordered pair once, as a `Coupling`:

| `Coupling` | Field |
|---|---|
| `a`, `b` | the two paths, in sorted order |
| `degree` | `couplingPercent` |
| `averageRevisions` | `averageChangeFrequency` |

Map every file that appears in a pair to a `File`:

| `File` | File field |
|---|---|
| `path` | `path` |
| `component` | `component`, or `null` |
| `health` | `codeHealth.value`, rounded to two decimals |
| `changes` | `changeFrequency` |
| `linesOfCode` | `linesOfCode` |
| `owner` | `knowledge.mainAuthor` as `{ name, ownership, isActive }` |
| `contributors` | `knowledge.contributors` as `{ name, ownership, isActive }`, in the order given |
| `team` | `team.mainTeam.name`, or `null` |

A partner that is not among the fetched files still gets a `File`, with its `path`, the `component` from the coupling entry, and `null` for the rest. Count them and add a note.

**3. Assess which coupling is a problem.** Change coupling is neither good nor bad; it depends on whether the architecture expects it. This is a judgement call, and yours to make, from the component names, the file names and paths, and what you know of the system. Aggregate the pairs by component first (sum `degree` × `averageRevisions` per pair of components, leaving out files without a component) and look at the strongest file pairs behind each dependency.

- Add an entry to `assessments` for each pair of components with coupling between them: `{ units, verdict, reason }`, where `verdict` is `"problematic"` or `"expected"` and `reason` is one plain sentence a software architect can check. For a problematic pair, add a `hypothesis` when the file names suggest one: one sentence on what probably drives the coupling, such as a shared type that keeps changing. The decoupling plan gives it to the coding agent to confirm or reject; leave it out rather than guess.
- **Expected:** coupling the design calls for. Examples: code and its tests (the renderer leaves test files out already); adapters or bindings whose job is to connect two layers; native code and its language bindings; a protocol or schema layer and the code that handles it; components within the same layer.
- **Problematic:** coupling that makes a change spread where it shouldn't. Examples: business logic or storage changing with views; a framework changing with the features built on it; consumers depending on raw internal types of another component; coupling with no architectural reason; a God Class that every change passes through.
- Name files whose coupling is bookkeeping in `expectedFiles`, as `{ path, reason }`: version files, changelogs or build configuration that every release touches. Their pairs are left out.

Pairs you don't assess fall back to a rule: coupling between files below Code Health 9.0 counts as problematic. Assess every pair of components you can, and say in the reason when a call is uncertain.

**4. Render.** Build a `ReportData` object that validates against the schema: `project` (with `id`), `analysisDate` (the results' `asOf`, as YYYY-MM-DD), `files`, `couplings` and `notes`. Copy the renderer to the user's output location as `{{project-slug}}-change-coupling.html`, and replace the stub inside its `{{REPORT_DATA}}` block. Leave the rest unchanged. Put only JSON there. Open the file in a browser and check that the matrix appears instead of an error box.

Use `notes` for what the reader needs to know about coverage: how many files were scanned, and how many coupled partners lack data.

**5. Record specifics.** Create or update the project notes from the template.

## How the renderer reads the data

- **Expected coupling:** pairs where one file is a test are left out of the analysis and counted in a footnote. Tests that co-evolve with their code are healthy coupling.
- **Units:** CodeScene's architectural components. Pairs with a file outside any component are left out; a footnote says how many, and how many co-changes they carry.
- **Co-changes:** for a pair of files, the commits that changed both, estimated as `degree` × `averageRevisions`, since CodeScene's coupling degree is shared commits relative to the pair's average. Summed per pair of units. A commit that touches several coupled files counts once per file pair, so co-changes measure the amount of coupled work, not the number of commits.
- **Matrix:** units × units. Problematic dependencies are red, darker the more co-changes; expected ones are muted grey; the diagonal, coupling within a unit, is neutral on its own scale. Hover a cell for its file pairs and assessment; click a problematic cell to jump to its card.
- **Coordination:** each file's contributors, normalised to shares that sum to 1. For a coupled pair, the part of its co-changes that crosses between people is 1 − Σ share_a(p) × share_b(p): 0 when one person wrote both files, close to 1 when different people did. Summed per pair of people, it shows who depends on whom. When teams are configured, the same view by main team follows.
- **Dependency cards:** the strongest problematic dependencies between units, with the reason from the assessment, each with its co-changes, the Code Health of the coupled files (weighted by co-changes), who knows each side, and a verdict. The file pairs behind a dependency are in its decoupling plan and in the matrix tooltip. *Refactor first* when the coupled files average below Code Health 4.0: both kinds of complexity meet, and moving complex code across a boundary only moves the complexity. *Decouple* otherwise: if the design doesn't expect the coupling, the code is healthy enough to restore locality of change. *Cross-developer dependency* when a third or more of the co-changes cross between people, and *Knowledge gap* when a main author is inactive.
- **Decoupling plans:** each dependency card has a *Decoupling plan* button. It opens a Markdown brief with *Copy* and *Download .md* buttons, for readers who don't have the code to hand it to a coding agent who does. The plan is filled in from the report data: the goal (a smaller blast radius of change), the reason and hypothesis, the strongest file pairs, how to diagnose from the commit history why the files change together, the strategy per cause, refactoring first when the coupled code is unhealthy, the people to involve, constraints, how the agent should work with the CodeScene tools, and when it is done. No model runs in the report; the coding agent does the reasoning, in the repository.
- **Coupling within components:** the strongest file pairs inside one unit.
- **Expected coupling:** a table of the expected dependencies and why.

## Rules learned the hard way

- **Main authors alone hide coordination.** When one person is the main author of most files, every pair looks like a one-person change, even where others wrote a large share. Use the contributors' shares, not only the main author.
- **Coupling is neither good nor bad.** Frame the findings as questions of architectural fit, not defects: a layered design expects some coupling between its layers. Leave out tests coupled to their code; that coupling is expected.
- **Don't colour coupling as good.** Strong problematic coupling should stand out in red; expected coupling stays muted, whatever its strength.
- **Don't call co-changes commits.** Summed over file pairs they count one commit many times. Label them co-changes and explain the estimate.
- **Keep the data complete; let the renderer filter.** Include files outside any component in the report data with `component: null`. The renderer leaves them out of the analysis and states how much it left out, so readers know when a missing component hides coupling.
- **Matrix keys go through HTML attributes.** Don't use control characters in keys that end up in `data-` attributes; the HTML parser replaces them. The renderer keys cells by index.
- Use CodeScene's theme colours and its three Code Health classes, as in the other reports: unhealthy (red) below 4.0, problematic (yellow) below 9.0, healthy (teal) from 9.0.

## Troubleshooting

- **No file has coupling:** the analysis has too little history, or change coupling is disabled for the project. The report says no coupling was found.
- **Nothing left after filtering:** the project has no architectural components, or the coupled files are all outside them. Ask the user to configure components in CodeScene and re-run the analysis.
- **MCP tools missing after the user re-enables the server:** ask the user to send a new message, then search again.
