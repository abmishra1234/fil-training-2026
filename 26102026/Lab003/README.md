# Lab 3 · Trigger evals

Part of **Tier 1 · Building Blocks for Skills** (FIL Gurgaon · AI Specialisation).

| Folder | Give to | Contents |
|---|---|---|
| `student/` | Students | your skill (weak description) + 3 decoy skills, prompt template, trigger_eval.py |
| `trainer/` | Trainer only | tuned description, reference 10-prompt set, before/after scores |

Start with `student/README.md` (students) or `trainer/README_TRAINER.md` (trainer).
Python 3.10+ · `pip install -r student/tools/requirements.txt`

LLM access is one switch in `.env` (copy `tools/.env.example` to `.env` in the lab folder):
`LLM_MODE=enterprise` (FIL AI Gateway, Azure AD token), `LLM_MODE=direct` (OpenAI-compatible
API key) or `LLM_MODE=mock` (offline). Then run `python tools/check_setup.py`.
See `SETUP_DIRECT_VS_ENTERPRISE.md`.
