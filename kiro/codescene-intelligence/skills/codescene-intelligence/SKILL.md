---
name: codescene-intelligence
description: Answers questions about a codebase from CodeScene's analysis through the CodeScene MCP server, and runs CodeScene's ready-made reports. Use when the user asks about Code Health, technical debt, hotspots, what to refactor first, code quality trends, who knows which code, key person risk or truck factor, change coupling between components, the outcome of refactoring, pull request or MCP safeguards, or wants a report on a CodeScene project or portfolio.
license: Apache-2.0
---

# CodeScene

The `codescene-intelligence` MCP server answers from CodeScene's latest analysis of the user's projects: Code Health, trends, hotspots, ownership and engineering outcomes. It reflects committed history as of that analysis. It can't see local or uncommitted changes.

## Start here

1. If the user hasn't named an account, call `list_accounts` to see which one is current. Use `switch_account` only when the user asks for another one.
2. Call `list_projects` to find the `project_id`. Match the repository the user is working in, or ask which project they mean when several match.
3. Pick the tool or report below that answers the question.

## Questions and the tools that answer them

| The user asks | Call |
|---|---|
| How healthy is this project? | `assess_project_code_health`, `get_code_health_trend` |
| What should we refactor first? | `list_prioritized_refactorings`, then `review_analyzed_file` for a file's Code Health issues |
| Where are the hotspots? Which components need attention? | `explore_project_components`, `explore_project_files` |
| Is Code Health getting worse anywhere? | `list_code_health_alerts`, `get_code_health_trend` |
| How active is development? | `get_commit_activity` |
| What would refactoring buy us? | `estimate_engineering_outcomes` (returns 90% intervals; say which point you show) |
| Do our pull request safeguards work? | `get_pull_request_safeguard_insights`, `get_pull_request_safeguard_outcomes` |
| Do developers use the local Code Health MCP? | `get_mcp_safeguard_insights`, `get_mcp_adoption` |

## Reports

For a full report, call `list_report_skills`, then `get_report_skill` with the skill id, and follow its instructions. Read the files it uses, such as the HTML renderer, with `get_report_skill_file`. The reports are:

| Skill id | What the user gets |
|---|---|
| `architectural-hotspots` | Components by change activity and Code Health, with the outcomes of uplifting the ones to address first |
| `refactoring-targets` | A prioritized refactoring backlog, with a refactoring spec per target to hand to a coding agent |
| `key-person-risk` | The truck factor and what leaves with each key person |
| `change-coupling` | Hidden dependencies between components from the commit history, and the coordination they force between people |
| `portfolio-overview` | A one-page summary of every project the user can access |
| `mcp-safeguard-insights` | How developers use the local Code Health MCP |
| `pull-request-safeguards` | How Code Health safeguards work on pull requests |
| `new-code-insights` | Whether last month's new code is healthy and AI-ready |
| `contributor-spotlight` | What one contributor built over the past year |

Offer a report when it answers the user's question better than a single tool call.

## Ground rules

- Use only data the CodeScene tools return. Never invent scores, counts or outcomes.
- If a call fails, show the error and stop the steps that depend on it. Never fill gaps with estimates.
- Never print or store credentials.
- To check code the user is editing right now, use the CodeScene Code Health power (`codescene-code-health`) if it is installed, or suggest the local Code Health MCP server or IDE extension. This server sees only analysed, committed code.
