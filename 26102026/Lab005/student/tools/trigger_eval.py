"""
trigger_eval.py - does your skill load at the right time?

    python tools/trigger_eval.py --skills skills/ [more/ …] --evals evals/triggers.jsonl \
                                 --target invoice-summary-formatter [--runs 3]

The model plays the agent's router. It sees ONLY the name + description of
every skill (Level 1 metadata), exactly like a real agent before loading.

Each line of triggers.jsonl:
  {"prompt": "Summarise this vendor invoice", "expected": "invoice-summary-formatter"}
  {"prompt": "Raise a PO for 20 chairs",      "expected": "NONE"}   <- near-miss
"expected" is the skill that SHOULD load, or NONE when your skill must stay quiet.

For the target skill we count:
  correct         router chose what was expected
  missed trigger  should have loaded the target, did not      -> fix 'Use when…'
  false trigger   loaded the target when it should not        -> fix 'Do not use for…'
  wrong other     a mix-up between OTHER skills (does not count against your skill)
Score = prompts where the target skill loaded exactly when it should.
"""
import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from skilllib import read_skill  # noqa: E402
from llm_adapter import chat  # noqa: E402

ROUTER = """You are the SKILL ROUTER of an AI agent at FIL.
You will see a user request and a list of installed skills (name: description).
Choose the ONE skill that should be loaded to handle the request, or NONE if no
skill clearly fits. Follow each description's 'Use when' and 'Do not use for'
clauses strictly. Reply with the skill name only, or NONE. No other words.

Installed skills:
{skills}"""


def load_skills(roots):
    """Each path is either one skill folder or a folder of skill folders."""
    skills = {}
    for root in roots:
        root = Path(root)
        dirs = [root] if (root / "SKILL.md").exists() else sorted(p for p in root.iterdir() if p.is_dir())
        for d in dirs:
            if (d / "SKILL.md").exists():
                front, _, _ = read_skill(d)
                desc = " ".join(str(front.get("description", "")).split())
                skills[str(front.get("name", d.name))] = desc
    return skills


def route(system, prompt, names):
    reply = chat(system, prompt).strip()
    for n in names:
        if re.search(rf"\b{re.escape(n)}\b", reply):
            return n
    return "NONE"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", required=True, nargs="+", help="skill folders, or folders of skills")
    ap.add_argument("--evals", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--runs", type=int, default=1, help="repeat each prompt (LLM routing is not 100% deterministic)")
    ap.add_argument("--csv", default="trigger_results.csv")
    a = ap.parse_args()

    skills = load_skills(a.skills)
    if a.target not in skills:
        sys.exit(f"Target '{a.target}' not found. Skills seen: {list(skills)}")
    system = ROUTER.format(skills="\n".join(f"- {n}: {d}" for n, d in skills.items()))
    evals = [json.loads(l) for l in Path(a.evals).read_text(encoding="utf-8").splitlines() if l.strip()]

    tally, rows = Counter(), []
    for e in evals:
        for r in range(a.runs):
            got = route(system, e["prompt"], list(skills))
            exp = e["expected"]
            if got == exp:
                kind = "correct"
            elif exp == a.target:
                kind = "missed trigger"
            elif got == a.target:
                kind = "false trigger"
            else:
                kind = "wrong other"
            tally[kind] += 1
            rows.append({"prompt": e["prompt"], "expected": exp, "got": got, "result": kind, "run": r + 1})
            flag = "OK " if kind == "correct" else "XX "
            print(f"{flag}{kind:<15} expected={exp:<28} got={got:<28} | {e['prompt']}")

    total = sum(tally.values())
    tp = sum(1 for r in rows if r["got"] == a.target and r["expected"] == a.target)
    fp = sum(1 for r in rows if r["got"] == a.target and r["expected"] != a.target)
    fn = sum(1 for r in rows if r["got"] != a.target and r["expected"] == a.target)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    print("\n" + "-" * 60)
    target_ok = total - tally["missed trigger"] - tally["false trigger"]
    print(f"Score: {target_ok}/{total}  (prompts where '{a.target}' loaded exactly when it should)")
    print(f"Missed triggers: {tally['missed trigger']}   False triggers: {tally['false trigger']}")
    print(f"Router picked exactly the expected skill: {tally['correct']}/{total}"
          + (f"   ({tally['wrong other']} wrong between OTHER skills: not your skill's problem)" if tally["wrong other"] else ""))
    print(f"Target precision: {prec:.2f}   recall: {rec:.2f}")
    with open(a.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Details saved to {a.csv}")


if __name__ == "__main__":
    main()
