# Lab 2 · Build an Action with a contract

Part of **Tier 1 · Building Blocks for Skills** (FIL Gurgaon · AI Specialisation).

| Folder | Give to | Contents |
|---|---|---|
| `student/` | Students | starter totals.py + schema, JSON inputs, 13 pytest tests |
| `trainer/` | Trainer only | reference script + schema (13/13), SKILL.md v2, MCP stretch server, test-by-test key |

Start with `student/README.md` (students) or `trainer/README_TRAINER.md` (trainer).
Python 3.10+ · `pip install -r student/tools/requirements.txt`

LLM access is one switch in `.env` (copy `tools/.env.example` to `.env` in the lab folder):
`LLM_MODE=enterprise` (FIL AI Gateway, Azure AD token), `LLM_MODE=direct` (OpenAI-compatible
API key) or `LLM_MODE=mock` (offline). Then run `python tools/check_setup.py`.
See `SETUP_DIRECT_VS_ENTERPRISE.md`.
