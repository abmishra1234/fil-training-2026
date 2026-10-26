# Peer review rubric (16 points)

Score each row 0, 1 or 2. **12 or more earns the Tier 1 Skill Builder badge.**

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| **Trigger** | Vague | 'Use when' only | 'Use when' + 'Do not use for', in users' words |
| **Instruction** | Missing parts | All parts, loose | All 5 parts, every rule testable |
| **Output contract** | "A good summary" | Fields named | Machine-checkable (fixed fields + status values) |
| **Knowledge / Asset split** | Mixed into SKILL.md | Partly moved out | Rules in references/, template in assets/ |
| **Action contract** | No schema | Schema, weak errors | Schema + actionable errors, no stack traces |
| **Permissions** | Not declared | Declared, too broad | Least privilege, gate PASS, no warnings |
| **Evals** | None | One surface only | Trigger evals + quality cases, scores recorded |
| **Classification** | None | One axis | Type + class, with a good reason |

## How to review (20 minutes)
1. Read SKILL.md first, *before* running anything. Could you follow it?
2. Run the four tools yourself; don't trust the other team's numbers.
3. Try to break it: one new near-miss prompt, one bad input to the script.
4. Write one **keep** (something they did well) and one **fix** (most important improvement).
