KIT ?= $(if $(wildcard kit/MANIFEST.sha256),kit,..)
GOLDEN ?= $(KIT)/evaluation/golden_set_dev.jsonl
DRAFTS ?= $(KIT)/evaluation/seeded_drafts_dev.jsonl
PY  ?= python
export PYTHONPATH := src

setup:            ## create venv deps
	$(PY) -m pip install -r requirements.txt

check:            ## Day 1 sanity check (corpus intact + LLM reachable)
	$(PY) scripts/check_setup.py

ingest:           ## build chunks + indexes
	curl -s -X POST localhost:8000/ingest || echo "start the API first (make api)"

api:
	uvicorn fundlens.api.main:app --reload --port 8000

ui:
	streamlit run ui/app.py

test:
	pytest -q

lint:
	ruff check src tests

predict:          ## run a golden set (GOLDEN=...) through your API + compliance check over seeded drafts (DRAFTS=...)
	$(PY) scripts/make_predictions.py --golden $(GOLDEN) --out reports/predictions.jsonl
	$(PY) scripts/make_predictions.py --drafts $(DRAFTS) --out reports/compliance_predictions.jsonl

eval: predict     ## score and write reports/eval_report.md
	$(PY) $(KIT)/evaluation/run_eval.py --golden $(GOLDEN) --predictions reports/predictions.jsonl \
	  --drafts $(DRAFTS) --compliance reports/compliance_predictions.jsonl --out reports/eval_report.md

smoke:            ## 10-question smoke eval for CI
	$(PY) scripts/make_predictions.py --golden $(KIT)/evaluation/golden_set_smoke10.jsonl --out reports/predictions_smoke.jsonl
	$(PY) $(KIT)/evaluation/run_eval.py --golden $(KIT)/evaluation/golden_set_smoke10.jsonl --predictions reports/predictions_smoke.jsonl --out reports/smoke_report.md
