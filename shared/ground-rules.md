# Ground rules for every skill

- Use only data returned by CodeScene's MCP tools. Never invent scores, counts or outcomes.
- If a call fails, show the error to the user and stop the steps that depend on it. Never fill gaps with estimates.
- Never print or store credentials.
- Keep skills and templates generic: no project names, people or numbers from a real analysis. Project-specific inputs and decisions live in the user's workspace.
- `estimate_engineering_outcomes` returns 90% intervals; say which point you show (the midpoint, unless the skill says otherwise).
