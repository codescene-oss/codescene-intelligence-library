# CodeScene intelligence library

Reusable skills and report templates that turn CodeScene's analysis into reports, through the CodeScene MCP server. Clients fetch them as they are, or copy and adapt them into their own.

Everything here is generic: no project names, people or analysis numbers. Project-specific inputs and decisions live in the client's own workspace, created from each skill's `templates/`.

## Skills

| Skill | Summary |
|---|---|
| [architectural-hotspots](skills/architectural-hotspots/SKILL.md) | Components in PAID quadrants by change activity and Code Health, with outcomes and team ROI for uplifting the ones to address first. [Details](#architectural-hotspots) |
| [refactoring-targets](skills/refactoring-targets/SKILL.md) | CodeScene's uplift targets as a prioritized refactoring backlog for an engineering manager: why each file, where to start, who to involve, the risks to plan for and the estimated outcome, plus a refactoring spec per primary and secondary target to hand to a coding agent. [Details](#refactoring-targets) |
| [key-person-risk](skills/key-person-risk/SKILL.md) | The project's truck factor and what leaves with each key person: CodeScene's off-boarding risks, the uplift targets that depend on one person, and the Code Health and coverage of that code. [Details](#key-person-risk) |
| [change-coupling](skills/change-coupling/SKILL.md) | The cost of change for software architects: logical dependencies between components mined from change coupling, the coordination they force between people, and how hard each is to break given the Code Health of the coupled code. [Details](#change-coupling) |
| [portfolio-overview](skills/portfolio-overview/SKILL.md) | A one-page summary of every project you can access, for technical leaders and managers: what works well, where attention is needed, and how much of the code is AI-optimal, by hotspot Code Health. [Details](#portfolio-overview) |
| [mcp-safeguard-insights](skills/mcp-safeguard-insights/SKILL.md) | How a project's developers use the local Code Health MCP: safeguard checks, degradations prevented before commit, uplifts, the trend over a year, the most active users and out-of-date installations. [Details](#mcp-safeguard-insights) |

## Adding a skill

Each skill is a folder with the same layout:

```
catalog.json                     index of all skills; what clients fetch first
shared/                          rules and docs every skill follows
skills/<id>/
  SKILL.md                       the workflow: which MCP tools to call and how to read their results
  skill.json                     metadata: version, MCP tools used, inputs, renderers
  report-data.schema.json        the report's data contract, independent of any renderer
  renderers/                     self-contained HTML + SVG reports with a {{REPORT_DATA}} block
  templates/                     placeholder files for project-specific notes
  examples/                      sample report data for trying the renderer
```

1. Create `skills/<id>/` with the files above. List every MCP tool the skill calls in `skill.json`.
2. Keep project specifics out: use `{{placeholders}}` in templates and the `{{REPORT_DATA}}` block in renderers.
3. Add the skill to the table above and the details below, and run `python scripts/validate.py --fix` to add it to `catalog.json`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution rules and how to run the checks locally.

## Releases

Each [GitHub release](https://github.com/codescene-oss/codescene-intelligence-library/releases) has a `codescene-intelligence-library-<version>.zip` with what clients need: `catalog.json`, `LICENSE`, `shared/` and `skills/`. Its `MANIFEST.json` lists the sha256 of every file, and the release carries the zip's checksum. Check a download for corruption with:

```bash
shasum -a 256 -c codescene-intelligence-library-<version>.zip.sha256
```

The checksum sits next to the zip, so it can't prove where the zip came from. Clients that sync a release should pin the zip's sha256 next to the version they pin.

## Skill details

### Architectural hotspots

Shows where in the architecture technical debt costs the most, and what paying it down would buy.

![Architectural hotspots report](docs/images/architectural-hotspots.png)

The report is a single HTML file with no dependencies, so it opens in any browser and prints to PDF. It contains:

- **A quadrant chart** of the architectural components. The horizontal axis is change activity, the vertical axis is Code Health, and bubble size is lines of code. Components that would overlap within a quadrant merge into a numbered group; hover to list them, click to spread them out.
- **An Address-first table** with each component's Code Health, trend, hotspots and worst file.
- **Estimated outcomes** of uplifting the Address components: fewer defects, less development time, higher productivity, and the hours a team would get back.

#### The PAID model

PAID is Gartner's model for prioritizing technical debt. It places each item on two axes, business impact and risk, and sorts it into one of four quadrants:

| Quadrant | Impact | Risk | Action |
|---|---|---|---|
| **Plan** | High | Low | Maintain; guard it so debt doesn't creep in |
| **Address** | High | High | Fix now; this debt taxes most of the delivery work |
| **Ignore** | Low | Low | No action |
| **Delay** | Low | High | Real debt, but cheap to carry; revisit if work shifts there |

The report measures both axes with CodeScene data. Impact is change activity: how much of the team's development runs through a component. Risk is low Code Health. Change activity follows a power law, so the split between busy and quiet uses head/tail breaks, cutting at the mean; the split between healthy and unhealthy is Code Health 9.0. The result separates the debt worth paying down from the debt that can safely wait.

### Refactoring targets

Turns CodeScene's uplift targets into a refactoring backlog that an engineering manager can plan from.

![Refactoring targets report](docs/images/refactoring-targets.png)

Uplift targets are unhealthy files that the team changes often, so refactoring them pays back in everyday delivery. CodeScene picks **primary** and **secondary** targets across the whole project, and **local** targets within each architectural component. The report keeps that order and, within each type, puts the most-changed file first. It contains:

- **A summary** of how many targets there are, how often the team changes them, their size, and how many need extra planning.
- **A backlog table** with one row per target: Code Health, commits, size, main author and the risks to plan for.
- **A card per target** with the evidence: the functions to start with, the Code Health issues, the files that change together with it, its Code Health trend, and the estimated outcome of refactoring it.
- **Who to involve:** the targets grouped by main author, flagging authors who are no longer active.
- **A refactoring spec** for each primary and secondary target, behind a *Refactoring spec* button. It's a Markdown brief for a coding agent: the goal, the functions to refactor in CodeScene's priority order with their evidence and CodeScene's guidance per Code Health issue, what to check first, constraints, and when the work is done. Copy it or download it as a `.md` file. The spec also tells the agent to refresh the data with the CodeScene MCP server, propose a plan for approval, and check Code Health after every step.

The risks are derived from the data. *Declining* means Code Health is getting worse, so the cost grows the longer it waits. *Knowledge risk* means most of the code would leave with its main author or already has. *Needs tests first* means line coverage is low or unknown, so add tests before refactoring.

### Key person risk

Answers a simple question in truck factor terms: what leaves when someone leaves?

![Key person risk report](docs/images/key-person-risk.png)

The truck factor is the smallest number of people who could leave before a large part of the code has no one who knows it. Knowledge concentrated in one person matters most where the code is also hard to learn (low Code Health), unsafe to change (low test coverage) and needed often. The report therefore stays with CodeScene's off-boarding risks and uplift targets. It contains:

- **The project's truck factor:** an estimate from CodeScene's main-author data, naming the people it depends on.
- **What leaves with each person:** one bar per person, one block per file they mainly know, sized by commits. Off-boarding risks stand out in red, labelled with how much knowledge would remain; everything else is muted.
- **A card per off-boarding risk:** who holds the knowledge, how much would remain if they left, Code Health now and a year ago, coverage, and a concrete action, such as adding tests, then refactoring together with the next contributor.
- **People:** a sortable table of off-boarding risks, truck factor 1 files, and the Code Health and coverage of the code each person mainly knows.
- **Components** led by one person or holding off-boarding risks, and **knowledge already lost** to former contributors.

### Change coupling

Shows the cost of change: where a change refuses to stay local, and what it takes to fix that.

![Change coupling report](docs/images/change-coupling.png)

Complexity comes in two shapes: code that is hard to understand on its own, which Code Health measures, and code that looks simple but behaves anything but because of its dependencies. Static dependency graphs list every dependency and miss the logical ones. Change coupling comes from developer behaviour instead: files that keep co-evolving in the same commits. The report lifts CodeScene's file-level change coupling to the architecture. It contains:

- **A component matrix** of co-changes. Problematic dependencies between components stand out in red; expected ones stay muted. The agent running the skill judges which is which from the architecture, and gives a reason for each.
- **A card per problematic dependency** with its co-changes, the Code Health of the coupled files, who knows each side, a verdict and a decoupling plan to hand to a coding agent. The verdict is *Refactor first* where both kinds of complexity meet, *Decouple* where the code is healthy enough to restore locality of change.
- **Coordination:** pairs of people whose code changes together, from each file's knowledge distribution. Code that logically belongs together but is maintained by different people; Conway's law, measured.

Change coupling is neither good nor bad, so the report separates the expected from the expensive: tests that co-evolve with their code are left out, and files outside any architectural component are left out with a footnote saying how much.

### Portfolio overview

Answers two questions a technical leader asks across all projects: what works well, and where is my attention needed?

![Portfolio overview report](docs/images/portfolio-overview.png)

Hotspots are the code the teams change most, so their Code Health decides how fast and safely a project delivers. The report places every project in one tier by hotspot Code Health:

| Tier | Hotspot Code Health |
|---|---|
| **Call to action** | below 4.0 |
| **Needs attention** | 4.0 to below 9.0 |
| **Healthy** | 9.0 to below 9.5 |
| **AI-optimal** | 9.5 and up: where AI assistants and people both work at their best, and a common goal |

It contains:

- **A summary** with the projects per tier and the share of all code that sits in AI-optimal projects.
- **A chart** of every project's hotspot Code Health, now and a year ago, over the four tier bands.
- **Where your attention is needed:** a card per project below 9.0, calls to action first, with its flags and a next step that points to the deeper report: *Refactoring targets*, *Architectural hotspots* or *Key person risk*. A **watch list** adds healthy projects with warning signs.
- **What works well:** the AI-optimal and healthy projects, and how far each healthy one is from 9.5.
- **All projects** in a sortable table, and the projects without Code Health data.

Flags never change a tier; they rank projects within one. They cover a twelve-month decline or improvement, uplift targets, unhealthy hotspots, off-boarding risks, Code Health alerts and dormant projects.

### MCP safeguard insights

Shows what the local Code Health MCP does for a project: how often developers and their AI assistants check Code Health while they code, and what those checks catch.

![MCP safeguard insights report](docs/images/mcp-safeguard-insights.png)

The data is live product telemetry, so it reflects use as of the moment the report is built, not the latest analysis. The report contains:

- **A summary** of the last week or month against the one before: active users, degradations prevented before commit and Code Health uplifts.
- **The year at a glance:** active users and impact per period.
- **The most active users**, by safeguard checks, with each person's previous period, who is new and who stopped. Names only: the report never shows email addresses.
- **How much each developer uses it**, as a distribution, and **which MCP tools** the checks come from.
- **Installations** per version, so outdated ones stand out, and **totals**: safeguard checks and all-time figures.

## License

Licensed under the [Apache License 2.0](LICENSE).
