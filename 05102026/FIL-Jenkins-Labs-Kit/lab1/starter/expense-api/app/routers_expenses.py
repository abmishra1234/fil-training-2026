"""API 2 - GET /api/v1/expenses              (filtering + row-level scope, A01/A05)
   API 3 - POST /api/v1/expenses/{id}/decision (RBAC + BOLA + SoD + workflow, A01/A06/A10)"""
import hashlib
import json
import re
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from .deps import get_current_user, require_role
from .errors import ApiError, forbidden, not_found, validation
from .http_utils import has_control_chars, read_json_object, reject_unknown_fields
from .logging_utils import log_event
from .store import CATEGORIES, STATUSES, User, public_view

router = APIRouter(prefix="/api/v1/expenses")

ALLOWED_PARAMS = {"status", "category", "employee_id", "from_date", "to_date",
                  "min_amount", "max_amount", "q", "sort", "page", "page_size"}
SORTS = {"expense_date", "amount_paise", "submitted_at"}
ID_RE = re.compile(r"[1-9][0-9]{0,9}")
AMOUNT_MAX = 100_000_000
IDEMPOTENCY_RE = re.compile(r"[A-Za-z0-9-]{8,64}")


# ------------------------------------------------------------------ query parsing
def _parse_date(name, raw):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise validation(f"{name} must be YYYY-MM-DD", name)
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise validation(f"{name} is not a valid date", name) from None


def _parse_int(name, raw, lo, hi, max_digits):
    if not re.fullmatch(rf"\d{{1,{max_digits}}}", raw) or not lo <= int(raw) <= hi:
        raise validation(f"{name} must be an integer between {lo} and {hi}", name)
    return int(raw)


def parse_filters(request: Request) -> dict:
    items = request.query_params.multi_items()
    seen = set()
    for k, _ in items:
        if k not in ALLOWED_PARAMS:
            raise validation("Unknown query parameter", k[:50])
        if k in seen:                                  # HTTP parameter pollution
            raise validation("Query parameter supplied more than once", k)
        seen.add(k)
    p = dict(items)
    f = {"page": 1, "page_size": 20, "sort": "-submitted_at"}
    if "status" in p:
        vals = p["status"].split(",")
        if not all(v in STATUSES for v in vals):
            raise validation("status must be a comma-separated list of " + ", ".join(STATUSES), "status")
        f["status"] = set(vals)
    if "category" in p:
        if p["category"] not in CATEGORIES:
            raise validation("category is not valid", "category")
        f["category"] = p["category"]
    if "employee_id" in p:
        if not ID_RE.fullmatch(p["employee_id"]):
            raise validation("employee_id must be a positive integer", "employee_id")
        f["employee_id"] = int(p["employee_id"])
    for name in ("from_date", "to_date"):
        if name in p:
            f[name] = _parse_date(name, p[name])
    if "from_date" in f and "to_date" in f and f["from_date"] > f["to_date"]:
        raise validation("from_date must not be after to_date", "from_date")
    for name in ("min_amount", "max_amount"):
        if name in p:
            f[name] = _parse_int(name, p[name], 0, AMOUNT_MAX, 9)
    if "min_amount" in f and "max_amount" in f and f["min_amount"] > f["max_amount"]:
        raise validation("min_amount must not exceed max_amount", "min_amount")
    if "q" in p:
        q = p["q"]
        if not 1 <= len(q) <= 50 or has_control_chars(q):
            raise validation("q must be 1-50 printable characters", "q")
        f["q"] = q.casefold()
    if "sort" in p:
        if p["sort"].lstrip("-") not in SORTS or p["sort"].count("-") > 1:
            raise validation("sort must be one of " + ", ".join(sorted(SORTS)) + " (prefix - for descending)", "sort")
        f["sort"] = p["sort"]
    if "page" in p:
        f["page"] = _parse_int("page", p["page"], 1, 10000, 5)
    if "page_size" in p:
        f["page_size"] = _parse_int("page_size", p["page_size"], 1, 100, 3)
    return f


def _matches(e: dict, f: dict) -> bool:
    # Filters only NARROW the caller's visible set - they can never widen it.
    if "status" in f and e["status"] not in f["status"]:
        return False
    if "category" in f and e["category"] != f["category"]:
        return False
    if "employee_id" in f and e["employee_id"] != f["employee_id"]:
        return False
    d = date.fromisoformat(e["expense_date"])
    if "from_date" in f and d < f["from_date"]:
        return False
    if "to_date" in f and d > f["to_date"]:
        return False
    if "min_amount" in f and e["amount_paise"] < f["min_amount"]:
        return False
    if "max_amount" in f and e["amount_paise"] > f["max_amount"]:
        return False
    if "q" in f and f["q"] not in e["description"].casefold():   # literal match, no wildcards
        return False
    return True


@router.get("")
def list_expenses(request: Request, user: User = Depends(get_current_user)):
    f = parse_filters(request)
    store = request.app.state.store
    with store.lock:
        rows = [dict(e) for e in store.visible_expenses(user) if _matches(e, f)]
    field = f["sort"].lstrip("-")
    rows.sort(key=lambda e: e["id"])                                   # deterministic tie-break
    rows.sort(key=lambda e: e[field], reverse=f["sort"].startswith("-"))  # stable sort
    start = (f["page"] - 1) * f["page_size"]
    page = rows[start:start + f["page_size"]]
    return {"items": [public_view(e) for e in page], "page": f["page"],
            "page_size": f["page_size"], "total": len(rows)}


# ------------------------------------------------------------------ decision
def _validate_decision(body: dict) -> dict:
    reject_unknown_fields(body, {"decision", "comment"})
    decision = body.get("decision")
    if decision not in ("APPROVE", "REJECT") or not isinstance(decision, str):
        raise validation("decision must be APPROVE or REJECT", "decision")
    comment = body.get("comment")
    if comment is not None and (not isinstance(comment, str) or len(comment) > 500):
        raise validation("comment must be a string of at most 500 characters", "comment")
    if decision == "REJECT" and (comment is None or len(comment.strip()) < 10):
        raise validation("A rejection needs a comment of at least 10 characters", "comment")
    return {"decision": decision, "comment": comment}


@router.post("/{expense_id}/decision")
async def decide(expense_id: str, request: Request, user: User = Depends(get_current_user)):
    st = request.app.state
    store = st.store
    # 1. role (403) - before we reveal anything about the object
    require_role(user, "MANAGER", "FINANCE_ADMIN", request=request)
    # 2. input validation (400)
    if not ID_RE.fullmatch(expense_id):
        raise validation("expense id must be a positive integer", "expense_id")
    key = request.headers.get("idempotency-key")
    if key is None or not IDEMPOTENCY_RE.fullmatch(key):
        raise validation("Idempotency-Key header is required (8-64 chars: letters, digits, -)",
                         "Idempotency-Key")
    body = _validate_decision(await read_json_object(request, st.settings.max_body_bytes))
    fingerprint = hashlib.sha256(json.dumps([expense_id, body], sort_keys=True).encode()).hexdigest()

    with store.lock:                                   # the whole check-then-act is atomic
        e = store.expenses.get(int(expense_id))
        # 3. object-level authorization (404 hides existence)
        if e is None or not store.can_see(user, e):
            log_event("access_denied", "WARNING", user_id=user.id, expense_id=int(expense_id), reason="not_visible")
            raise not_found()
        # 4. separation of duties
        if e["employee_id"] == user.id:
            log_event("access_denied", "WARNING", user_id=user.id, expense_id=e["id"], reason="self_approval")
            raise forbidden("You cannot decide on your own expense claim", "self_approval_forbidden")
        # 5. idempotent replay
        prior = store.idempotency.get((user.id, key))
        if prior is not None:
            if prior[0] != fingerprint:
                raise ApiError(409, "idempotency_conflict",
                               "Idempotency-Key was already used with a different request")
            return JSONResponse(prior[1])
        # 6. workflow state machine
        if user.role == "MANAGER":
            if e["status"] != "SUBMITTED":
                raise ApiError(409, "invalid_state", "Expense is not awaiting your decision")
            if body["decision"] == "REJECT":
                new = "REJECTED"
            else:
                new = "APPROVED" if e["amount_paise"] <= store.approval_threshold else "PENDING_FINANCE"
        else:  # FINANCE_ADMIN
            if e["status"] != "PENDING_FINANCE":
                raise ApiError(409, "invalid_state", "Expense is not awaiting a finance decision")
            new = "APPROVED" if body["decision"] == "APPROVE" else "REJECTED"
        old = e["status"]
        e["status"] = new
        result = public_view(e)
        store.idempotency[(user.id, key)] = (fingerprint, result)
    log_event("expense_decided", user_id=user.id, expense_id=e["id"], from_status=old, to_status=new)
    return JSONResponse(result)
