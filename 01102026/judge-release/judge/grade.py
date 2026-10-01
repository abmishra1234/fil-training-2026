#!/usr/bin/env python3
"""Expense Claims API Challenge - judge / scoreboard.

usage:  python grade.py                 # full run, all 10 categories (100 points)
        python grade.py authn token     # only some categories
        python grade.py --start-cmd "java -jar target/app.jar" --workdir ../my-api

Writes reports/judge_report.md, reports/judge_report.html and reports/judge_report.json
(attach the .md/.html summary to slide 3 of your presentation)."""
import argparse
import html
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ["AUTHN", "TOKEN", "RBAC", "OBJECT", "FILTER", "INPUT", "WORKFLOW", "CONFIG", "LOGGING", "RESILIENCE"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("categories", nargs="*", help="subset of: " + " ".join(c.lower() for c in ORDER))
    ap.add_argument("--start-cmd"), ap.add_argument("--workdir")
    ap.add_argument("--team", default=os.environ.get("JUDGE_TEAM", "unnamed-team"))
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()

    env = dict(os.environ)
    if a.start_cmd:
        env["JUDGE_START_CMD"] = a.start_cmd
    if a.workdir:
        env["JUDGE_WORKDIR"] = str(Path(a.workdir).resolve())
    cats = [c.upper() for c in a.categories]
    bad = [c for c in cats if c not in ORDER]
    if bad:
        sys.exit(f"unknown category: {bad}")
    env["JUDGE_CATS"] = ",".join(cats)
    fd, res_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    env["JUDGE_RESULTS"] = res_path

    t0 = time.time()
    cmd = [sys.executable, "-m", "pytest", "-q", "--no-header", "-rN" if not a.verbose else "-rf"]
    subprocess.run(cmd, cwd=HERE, env=env)
    elapsed = time.time() - t0
    data = json.loads(Path(res_path).read_text() or "{}")
    results, names = data.get("results", []), data.get("categories", {})

    per = OrderedDict((c, {"passed": 0, "total": 0}) for c in ORDER if not cats or c in cats)
    for r in results:
        if r["category"] in per:
            per[r["category"]]["total"] += 1
            per[r["category"]]["passed"] += r["outcome"] == "passed"
    score = 0.0
    rows = []
    for c, v in per.items():
        pts = 10 * v["passed"] / v["total"] if v["total"] else 0.0
        score += pts
        rows.append((c, names.get(c, c), v["passed"], v["total"], pts))
    max_score = 10 * len(per)
    passed = sum(v["passed"] for v in per.values())
    total = sum(v["total"] for v in per.values())

    print("\n" + "=" * 78)
    print(f" EXPENSE CLAIMS API CHALLENGE - JUDGE REPORT   team: {a.team}")
    print("=" * 78)
    print(f" {'CATEGORY':<11} {'WHAT IT CHECKS':<42} {'TOTAL':>5} {'PASS':>5} {'FAIL':>5} {'POINTS':>7}")
    for c, n, p, t, pts in rows:
        print(f" {c:<11} {n[:42]:<42} {t:>5} {p:>5} {t - p:>5} {pts:7.1f}")
    print("-" * 78)
    print(f" {'TOTAL':<54} {total:>5} {passed:>5} {total - passed:>5} {score:7.1f} / {max_score}")
    print("=" * 78)

    failed = [r for r in results if r["outcome"] != "passed"]
    out = HERE / "reports"
    out.mkdir(exist_ok=True)
    meta = {"team": a.team, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "duration_s": round(elapsed, 1),
            "python": platform.python_version(), "start_cmd": env.get("JUDGE_START_CMD") or "judge_config.json"}
    (out / "judge_report.json").write_text(json.dumps(
        {"meta": meta, "score": round(score, 1), "max_score": max_score, "passed": passed, "total": total,
         "failed": total - passed,
         "categories": [dict(code=c, name=n, total=t, passed=p, failed=t - p, points=round(pts, 1)) for c, n, p, t, pts in rows],
         "results": results}, indent=2))

    md = [f"# Judge report - {a.team}", "",
          f"**Score: {score:.1f} / {max_score}**  ·  {passed} passed · {total - passed} failed · {total} total  ·  {meta['generated_at']}  ·  {elapsed:.0f}s", "",
          "## Result matrix (copy to slide 3)", "",
          "| Category | What it checks | Total | Passed | Failed | Points |", "|---|---|---:|---:|---:|---:|"]
    md += [f"| {c} | {n} | {t} | {p} | {t - p} | {pts:.1f} |" for c, n, p, t, pts in rows]
    md += [f"| **Total** | | **{total}** | **{passed}** | **{total - passed}** | **{score:.1f}** |", ""]
    if failed:
        md += ["## Failed tests", "", "| Test | Category | Reason |", "|---|---|---|"]
        md += [f"| {r['title']} | {r['category']} | {r['message'].replace('|', '/')[:160]} |" for r in failed]
    (out / "judge_report.md").write_text("\n".join(md) + "\n")
    (out / "judge_report.html").write_text(render_html(a.team, meta, rows, score, max_score, passed, total, failed))
    print(f" reports written to {out}/judge_report.(md|html|json)\n")
    return 0 if not failed else 1


def render_html(team, meta, rows, score, max_score, passed, total, failed):
    e = html.escape
    bars = "".join(
        f"<tr><td class=c>{e(c)}</td><td>{e(n)}</td><td class=n>{t}</td><td class=n>{p}</td><td class=n style=color:{'#8a2a2a' if t - p else '#5b6475'}>{t - p}</td>"
        f"<td><div class=bar><span style='width:{(p / t * 100) if t else 0:.0f}%'></span></div></td>"
        f"<td class=n><b>{pts:.1f}</b></td></tr>" for c, n, p, t, pts in rows)
    fails = "".join(f"<tr><td>{e(r['title'])}</td><td class=c>{e(r['category'])}</td><td class=m>{e(r['message'][:200])}</td></tr>"
                    for r in failed) or "<tr><td colspan=3>None - every test passed.</td></tr>"
    return f"""<!doctype html><html><head><meta charset=utf-8><title>Judge report - {e(team)}</title><style>
body{{font:14px/1.45 system-ui,Segoe UI,Arial,sans-serif;margin:32px;color:#1d2433;background:#fff}}
h1{{margin:0 0 4px;font-size:22px}} .sub{{color:#5b6475;margin-bottom:20px}}
.score{{font-size:40px;font-weight:700;color:#0f5c4a}} table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}
td,th{{padding:7px 10px;border-bottom:1px solid #e3e7ee;text-align:left;vertical-align:top}} th{{background:#f4f6f9}}
.c{{font-family:ui-monospace,Consolas,monospace;font-weight:600}} .n{{text-align:right;white-space:nowrap}}
.bar{{background:#e8ecf2;border-radius:4px;height:10px;width:160px}} .bar span{{display:block;height:10px;border-radius:4px;background:#1a8a6e}}
.m{{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#8a2a2a}}</style></head><body>
<h1>Expense Claims API Challenge - Judge report</h1>
<div class=sub>Team <b>{e(team)}</b> · {e(meta['generated_at'])} · {meta['duration_s']} s · start: <code>{e(meta['start_cmd'])}</code></div>
<div class=score>{score:.1f} <small style="font-size:18px;color:#5b6475">/ {max_score} · {passed} passed · {total - passed} failed</small></div>
<table><tr><th>Category</th><th>What it checks</th><th class=n>Total</th><th class=n>Passed</th><th class=n>Failed</th><th></th><th class=n>Points</th></tr>{bars}
<tr><td class=c>TOTAL</td><td></td><td class=n><b>{total}</b></td><td class=n><b>{passed}</b></td><td class=n><b>{total - passed}</b></td><td></td><td class=n><b>{score:.1f}</b></td></tr></table>
<h2 style="font-size:16px">Failed tests</h2><table><tr><th>Test</th><th>Category</th><th>Reason</th></tr>{fails}</table>
</body></html>"""


if __name__ == "__main__":
    sys.exit(main())
