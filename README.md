# CodeScene intelligence library

Reusable skills and report templates that turn CodeScene's analysis into reports, through the CodeScene MCP server. Clients fetch them as they are, or copy and adapt them into their own.

Everything here is generic: no project names, people or analysis numbers. Project-specific inputs and decisions live in the client's own workspace, created from each skill's `templates/`.

## Skills

| Skill | Summary |
|---|---|
| [architectural-hotspots](skills/architectural-hotspots/SKILL.md) | Components in PAID quadrants by change activity and Code Health, with outcomes and team ROI for uplifting the ones to address first. [Details](#architectural-hotspots) |

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
