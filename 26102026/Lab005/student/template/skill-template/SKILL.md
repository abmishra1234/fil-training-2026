---
name: your-skill-name
description: Use when … Do not use for …
allowed-tools: Read Bash(python:scripts/*)
metadata:
  skill-class: …            # capability-uplift | encoded-preference
  skill-type: …             # atomic | composite | policy | agent-profile
  owner: …                  # who owns the knowledge, who owns the scripts
  fil.permissions:
    data_scopes: […]
    network_egress: none
    writes: none
    credentials: none
    side_effects: none
---

## Role
You are …

## Procedure
1. …
2. Pipe the extracted data as JSON to `python scripts/<your_action>.py --data ../mock_connectors/<file>.json`
3. If it returns an "error", follow its "fix" …
4. Fill assets/<template>.md …

## Decision rules
- If … then …

## Output contract
… then `Status: <…>` and `Notes: <one sentence>`

## Examples
…
