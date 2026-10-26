# Lab 5 · Capstone: ship a complete Tier 1 skill  (student copy)

**Time:** 45 min build + 20 min peer review + 2 min demo per team · **Teams of 3**
**Badge:** 🏅 Tier 1 Skill Builder
**Primitives practised:** all eight

## Your mission

Pick **one brief** from `briefs/` and ship a complete skill folder that a reviewer could
install tomorrow. Everything you practised in Labs 1–4 comes together here.

| Brief | Skill name | Mock connector |
|---|---|---|
| A | `expense-claim-checker` | `mock_connectors/hr_employees.json` |
| B | `leave-balance-explainer` | `mock_connectors/hr_employees.json` |
| C | `meeting-minutes-formatter` | `mock_connectors/calendar_events.json` + `hr_employees.json` |

## Suggested roles

* **Domain author:** Instruction, Trigger, Knowledge, Asset
* **Engineer:** Action (script + schema), Permission manifest, gate
* **Tester:** trigger evals, quality cases, runs every tool, keeps the scoreboard

Rotate who presents the demo.

## Folder you start with

```
student/
├── briefs/               ← pick one
├── samples/              ← example user inputs for each brief
├── mock_connectors/      ← JSON stand-ins for the HR and calendar systems
├── decoys/               ← 5 other skills your trigger must compete with
├── template/skill-template/   ← copy this
├── rubric.md  peer_review_form.md
└── tools/                ← check_skill, gate, trigger_eval, run_cases
```

## Steps

1. Copy the template and rename it: `cp -r template/skill-template expense-claim-checker`
   (folder name = `name:` in SKILL.md).
2. **Instruction + Trigger (1, 2):** SKILL.md with all five sections; *Use when* / *Do not use for*.
3. **Knowledge + Asset (3, 5):** the brief's rules → `references/`; the output template → `assets/`.
4. **Action (4):** a script with a JSON Schema 2020-12 contract and actionable errors.
5. **Connector (6):** your script reads the mock JSON passed as `--data ../mock_connectors/…`.
   Say in SKILL.md which real system and MCP tool it stands in for.
6. **Permissions (7):** fill the manifest; `python tools/gate.py <skill>` → PASS.
7. **Evals (8):**
   * `evals/triggers.jsonl`: 6 prompts (3 positives + 3 near-misses, expected = a decoy or NONE)
   * `evals/quality_cases.jsonl`: 3 cases from `samples/`, each with the Action input JSON
     in `evals/inputs/`
8. **Classify** in the frontmatter `metadata`: `skill-type` (atomic / composite / policy /
   agent-profile) and `skill-class` (capability-uplift / encoded-preference). Be ready to defend it.
9. Run everything and record the numbers in `peer_review_form.md`
   (`.env` as in Lab 1; run `python tools/check_setup.py` first):
   ```bash
   python tools/check_skill.py  <skill>
   python tools/gate.py         <skill>
   python tools/trigger_eval.py --skills <skill> decoys --evals <skill>/evals/triggers.jsonl --target <skill>
   python tools/run_cases.py    <skill> <skill>/evals/quality_cases.jsonl
   ```
10. **Peer review** another team's folder with `rubric.md` (20 min). Give one *keep* and one *fix*.
11. **Demo** in 2 minutes: the problem, one live run, your before → after trigger score.

## Done when ✅

- [ ] All 8 primitives present (connector mocked)
- [ ] check_skill PASS · gate PASS · trigger score ≥ 5/6
- [ ] 3 quality cases match the contract
- [ ] Peer review score ≥ 12/16

## Hints

* Build the Action first and test it with plain JSON. Then write the instruction around it.
* Brief B: "5 days from 10 to 14 Nov" is not 5 working days. Let the script count.
* Brief C: "someone" is not an owner, and "by Sunday" is not a date.
* Keep SKILL.md short; put rules in `references/`.
