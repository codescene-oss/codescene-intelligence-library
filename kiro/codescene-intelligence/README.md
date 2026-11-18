<img src="logo.png" alt="CodeScene" width="80">

# CodeScene intelligence power for Kiro

Ask CodeScene about your code from Kiro: Code Health, hotspots, technical debt, what to refactor first, who knows which code, and what a refactoring would buy you. The power connects Kiro to the CodeScene MCP server and teaches the agent when to use it.

## What you get

- **Answers from CodeScene's analysis.** Code Health and its trend, hotspots, Code Health alerts, prioritized refactorings, commit activity and estimated engineering outcomes.
- **Ready-made reports** from the [CodeScene intelligence library](../../README.md#skills): architectural hotspots, refactoring targets, key person risk, change coupling, portfolio overview, new code insights, contributor spotlight, and how your pull request and MCP safeguards work.

Try asking:

- "What should we refactor first in this project?"
- "Who are the key people on this codebase, and what leaves with them?"
- "Give me a portfolio overview of our projects."

## Requirements

- A [CodeScene Cloud](https://codescene.io) account with at least one analysed project.
- Kiro. You sign in to CodeScene in your browser the first time the power connects.

The power connects to CodeScene Cloud at `https://codescene.io/mcp`. On-prem CodeScene: [import the power from a folder](https://kiro.dev/docs/powers/installation/) after changing the `url` in [mcp.json](mcp.json) to your server's `/mcp` endpoint.

## Install

In Kiro, open the Powers panel, choose **Add Custom Power**, then **Import power from GitHub**, and paste:

```
https://github.com/codescene-oss/codescene-intelligence-library/tree/main/kiro/codescene-intelligence
```

## What's in the power

| File | Purpose |
|---|---|
| [plugin.json](plugin.json) | The manifest, in the [Agent Plugins](https://agent-plugins.org/specification) format |
| [mcp.json](mcp.json) | The connection to the CodeScene MCP server |
| [skills/codescene-intelligence/SKILL.md](skills/codescene-intelligence/SKILL.md) | When to use CodeScene, which tool answers which question, and how to run the reports |

The report workflows come from the MCP server, so they stay current without updating the power.

## Privacy and support

- Privacy policy: [CodeScene Privacy Policy](https://codescene.com/hubfs/web_docs/CodeScene_Privacy_Policy.pdf)
- Support: [CodeScene Support Hub](https://supporthub.codescene.com/)
- Documentation: [codescene.io/docs](https://codescene.io/docs/)

## License

[Apache-2.0](../../LICENSE)
