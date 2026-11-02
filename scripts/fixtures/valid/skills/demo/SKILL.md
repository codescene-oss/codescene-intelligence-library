# Demo

Follow [the ground rules](../../shared/ground-rules.md). The report data follows [report-data.schema.json](report-data.schema.json), and [renderers/report.html](renderers/report.html) renders it. Save notes as `codescene/projects/{{project-slug}}.md` in the user's workspace. See [Workflow](#workflow).

## Workflow

1. Call `list_projects` to find the project.
2. Call `explore_project_files` and report each file's Code Health.
