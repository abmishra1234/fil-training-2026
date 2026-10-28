"""
02_datasets_and_evals.py - datasets + experiments on the FIL LangSmith (via the LangSmith SDK).

Traces go through OpenTelemetry (fil-aiobs). Datasets, experiments, prompts and feedback use the
LangSmith SDK against the FIL LangSmith REST API: <observability host>/api/v1  (LANGSMITH_ENDPOINT).

    python 02_datasets_and_evals.py --dry-run          # run + score locally, nothing uploaded
    python 02_datasets_and_evals.py                    # dataset + 2 experiments (basic vs mqr_rrf)
    python 02_datasets_and_evals.py --modes basic mqr_rrf vectorless --limit 6

Then in LangSmith: Datasets & Experiments -> rag-lab-golden -> select the experiments -> Compare.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import llm_client

ROOT = Path(__file__).resolve().parent

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--dataset", default="rag-lab-golden", help="dataset name in LangSmith")
parser.add_argument("--modes", nargs="+", default=["basic", "mqr_rrf"], help="RAG modes to compare")
parser.add_argument("--limit", type=int, default=0, help="only the first N questions (0 = all)")
parser.add_argument("--dry-run", action="store_true", help="score locally, upload nothing")
args = parser.parse_args()

questions = json.loads((ROOT / "data" / "eval_set.json").read_text(encoding="utf-8"))["questions"]
if args.limit:
    questions = questions[: args.limit]


# ---- evaluators: plain functions, arguments matched by name ------------------ #
def retrieved_fact(outputs: dict, reference_outputs: dict) -> dict:
    """1 if any chunk sent to the LLM contains the expected fact (retrieval quality)."""
    fact = reference_outputs["must_contain"].lower()
    hit = any(fact in (s.get("text") or "").lower() for s in outputs.get("sources", []))
    return {"key": "retrieved_fact", "score": int(hit)}


def answer_has_fact(outputs: dict, reference_outputs: dict) -> dict:
    """1 if the final answer itself mentions the expected fact (end-to-end quality)."""
    return {"key": "answer_has_fact", "score": int(reference_outputs["must_contain"].lower() in outputs["answer"].lower())}


def cites_sources(outputs: dict) -> dict:
    """1 if the answer cites at least one passage like [1]."""
    return {"key": "cites_sources", "score": int(bool(re.search(r"\[\d+\]", outputs["answer"])))}


EVALUATORS = [retrieved_fact, answer_has_fact, cites_sources]

# ---- target: the RAG app as a function --------------------------------------- #
llm_client.init_observability()
from app.pipeline import RagService  # noqa: E402  (after .env + telemetry)

service = RagService()
service.reindex()


def make_target(mode: str):
    def target(inputs: dict) -> dict:
        out = service.run(mode, inputs["question"])
        return {"answer": out["answer"], "sources": [{"source": s["source"], "text": s["text"]} for s in out["sources"]]}
    target.__name__ = f"rag_{mode}"
    return target


if args.dry_run:
    print(f"Dry run on {len(questions)} questions (nothing uploaded)\n")
    for mode in args.modes:
        target, totals = make_target(mode), {e.__name__: 0 for e in EVALUATORS}
        for q in questions:
            out = target({"question": q["question"]})
            ref = {"must_contain": q["must_contain"]}
            for e in EVALUATORS:
                kw = {"outputs": out, "reference_outputs": ref} if "reference_outputs" in e.__code__.co_varnames else {"outputs": out}
                totals[e.__name__] += e(**kw)["score"]
        print(f"{mode:<10} " + "  ".join(f"{k}={v}/{len(questions)}" for k, v in totals.items()))
    llm_client.flush_observability()
    raise SystemExit(0)

# ---- 1. dataset (same pattern as the FIL "Dataset generation using Python" page) #
client = llm_client.get_langsmith_client()
print("LangSmith API :", llm_client.obs_settings.api_url)
if client.has_dataset(dataset_name=args.dataset):
    dataset = client.read_dataset(dataset_name=args.dataset)
    print(f"Dataset       : {args.dataset} (exists, reused)")
else:
    dataset = client.create_dataset(dataset_name=args.dataset,
                                    description="RAG lab golden set: question -> fact that must be retrieved")
    client.create_examples(dataset_id=dataset.id, examples=[
        {"inputs": {"question": q["question"]},
         "outputs": {"must_contain": q["must_contain"]},
         "metadata": {"id": q["id"], "type": q["type"]}}
        for q in questions])
    print(f"Dataset       : {args.dataset} created with {len(questions)} examples")

# ---- 2. one experiment per mode -> compare them side by side in the UI -------- #
for mode in args.modes:
    results = client.evaluate(
        make_target(mode),
        data=args.dataset,
        evaluators=EVALUATORS,
        experiment_prefix=f"rag-{mode}",
        metadata={"mode": mode, "chat_model": llm_client.settings.chat_model, **llm_client.obs_settings.metadata},
        max_concurrency=2,
    )
    print(f"Experiment    : {results.experiment_name}")

llm_client.flush_observability()
print("\nOpen LangSmith -> Datasets & Experiments ->", args.dataset, "-> select the experiments -> Compare")
