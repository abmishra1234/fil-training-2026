"""Independent model of the specification, computed from the seed file.
Used to calculate the EXPECTED result of every filter/sort/page query."""
from datetime import date

from harness import SEED

USERS_BY_ID = {u["id"]: u for u in SEED["users"]}
USER_ID = {u["username"]: u["id"] for u in SEED["users"]}
EXPENSES = SEED["expenses"]
ITEM_FIELDS = {"id", "employee_id", "category", "amount_paise", "currency",
               "expense_date", "description", "status", "submitted_at"}


def visible(username: str) -> list[dict]:
    uid = USER_ID[username]
    role = USERS_BY_ID[uid]["role"]
    if role in ("FINANCE_ADMIN", "AUDITOR"):
        return list(EXPENSES)
    out = []
    for e in EXPENSES:
        owner = USERS_BY_ID[e["employee_id"]]
        if e["employee_id"] == uid or (role == "MANAGER" and owner["manager_id"] == uid):
            out.append(e)
    return out


def query(username: str, params: dict | None = None) -> dict:
    p = dict(params or {})
    rows = visible(username)
    if "status" in p:
        rows = [e for e in rows if e["status"] in p["status"].split(",")]
    if "category" in p:
        rows = [e for e in rows if e["category"] == p["category"]]
    if "employee_id" in p:
        rows = [e for e in rows if e["employee_id"] == int(p["employee_id"])]
    if "from_date" in p:
        rows = [e for e in rows if date.fromisoformat(e["expense_date"]) >= date.fromisoformat(p["from_date"])]
    if "to_date" in p:
        rows = [e for e in rows if date.fromisoformat(e["expense_date"]) <= date.fromisoformat(p["to_date"])]
    if "min_amount" in p:
        rows = [e for e in rows if e["amount_paise"] >= int(p["min_amount"])]
    if "max_amount" in p:
        rows = [e for e in rows if e["amount_paise"] <= int(p["max_amount"])]
    if "q" in p:
        rows = [e for e in rows if p["q"].casefold() in e["description"].casefold()]
    sort = p.get("sort", "-submitted_at")
    field = sort.lstrip("-")
    rows = sorted(rows, key=lambda e: e["id"])
    rows = sorted(rows, key=lambda e: e[field], reverse=sort.startswith("-"))
    page, size = int(p.get("page", 1)), int(p.get("page_size", 20))
    return {"ids": [e["id"] for e in rows[(page - 1) * size: page * size]], "total": len(rows)}
