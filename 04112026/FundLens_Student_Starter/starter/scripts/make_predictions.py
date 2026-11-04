"""Run every golden-set question through YOUR running API and write predictions for the scorer.

    python scripts/make_predictions.py --golden ../evaluation/golden_set_dev.jsonl --out reports/predictions.jsonl
    python scripts/make_predictions.py --drafts ../evaluation/seeded_drafts_dev.jsonl --out reports/compliance_predictions.jsonl

The second form calls your compliance_check function directly (no API needed).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fundlens.config import settings  # noqa: E402


def run_golden(golden: Path, out: Path) -> None:
    rows = [json.loads(line) for line in golden.read_text().splitlines() if line.strip()]
    out.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=settings.api_url, timeout=120) as http, out.open("w") as fh:
        for r in rows:
            t0 = time.time()
            if r["expected_route"] == "draft" and r.get("email_ref"):
                resp = http.post("/draft", json={"instruction": r["question"], "email_ref": r["email_ref"], "session_id": f"eval-{r['id']}"})
            else:
                resp = http.post("/ask", json={"question": r["question"], "session_id": f"eval-{r['id']}"})
            if resp.status_code != 200:
                pred = {"id": r["id"], "error": f"HTTP {resp.status_code}", "route": None, "answer": "", "citations": [],
                        "retrieved_doc_ids": [], "refused": False, "review_status": "n/a"}
            else:
                pred = {"id": r["id"], **resp.json()}
            pred.setdefault("latency_ms", int((time.time() - t0) * 1000))
            fh.write(json.dumps(pred) + "\n")
            print(f"{r['id']}: route={pred.get('route')} status={pred.get('review_status')}")


def run_drafts(drafts: Path, out: Path) -> None:
    from fundlens.tools.compliance import compliance_check
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for line in drafts.read_text().splitlines():
            d = json.loads(line)
            res = compliance_check(d["draft"])
            fh.write(json.dumps({"id": d["id"], "passed": res.passed, "violated_rule_ids": res.violated_rule_ids}) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", type=Path)
    ap.add_argument("--drafts", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.golden:
        run_golden(a.golden, a.out)
    elif a.drafts:
        run_drafts(a.drafts, a.out)
    else:
        ap.error("give --golden or --drafts")
