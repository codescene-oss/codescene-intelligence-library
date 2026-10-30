# CodeScene intelligence library

Reusable skills and report templates that turn CodeScene's analysis into reports, through the CodeScene MCP server. Clients fetch them as they are, or copy and adapt them into their own.

Everything here is generic: no project names, people or analysis numbers. Project-specific inputs and decisions live in the client's own workspace, created from each skill's `templates/`.

## Skills

| Skill | Summary |
|---|---|
| [architectural-hotspots](skills/architectural-hotspots/SKILL.md) | Components in PAID quadrants by change activity and Code Health, with outcomes and team ROI for uplifting the ones to address first. [Details](#architectural-hotspots) |
| [refactoring-targets](skills/refactoring-targets/SKILL.md) | CodeScene's uplift targets as a prioritized refactoring backlog for an engineering manager: why each file, where to start, who to involve, the risks to plan for and the estimated outcome, plus a refactoring spec per primary and secondary target to hand to a coding agent. [Details](#refactoring-targets) |

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
3. Add the skill to `catalog.json`, the table above and the details below.

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
