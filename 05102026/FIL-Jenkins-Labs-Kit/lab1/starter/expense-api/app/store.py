"""In-memory data store rebuilt from the seed file on every start.
A real system would use a database: keep the SAME rules (parameterised queries,
row locks / transactions) - only the storage changes."""
import json
import threading
from dataclasses import dataclass, field

from .security import hash_password

ROLES = {"EMPLOYEE", "MANAGER", "FINANCE_ADMIN", "AUDITOR"}
STATUSES = ("SUBMITTED", "PENDING_FINANCE", "APPROVED", "REJECTED")
CATEGORIES = ("TRAVEL", "MEALS", "LODGING", "TRAINING", "OFFICE_SUPPLIES", "INTERNET")
PUBLIC_FIELDS = ("id", "employee_id", "category", "amount_paise", "currency",
                 "expense_date", "description", "status", "submitted_at")


@dataclass
class User:
    id: int
    username: str
    role: str
    manager_id: int | None
    is_active: bool
    password_hash: str = field(repr=False)     # never serialised, never logged


class Store:
    def __init__(self, seed_path):
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        self.approval_threshold = int(data["approval_threshold_paise"])
        self.users: dict[int, User] = {}
        self.by_username: dict[str, User] = {}
        for u in data["users"]:
            assert u["role"] in ROLES
            user = User(u["id"], u["username"], u["role"], u["manager_id"], u["is_active"],
                        hash_password(u["password"]))      # plain text dropped here
            self.users[user.id] = user
            self.by_username[user.username] = user
        self.expenses: dict[int, dict] = {e["id"]: dict(e) for e in data["expenses"]}
        self.lock = threading.Lock()                        # A06/A10: atomic transitions
        self.idempotency: dict[tuple[int, str], tuple[str, dict]] = {}

    # ---- authorization scope (A01) -------------------------------------------------
    def can_see(self, user: User, expense: dict) -> bool:
        if user.role in ("FINANCE_ADMIN", "AUDITOR"):
            return True
        owner = self.users.get(expense["employee_id"])
        if expense["employee_id"] == user.id:
            return True
        return user.role == "MANAGER" and owner is not None and owner.manager_id == user.id

    def visible_expenses(self, user: User) -> list[dict]:
        return [e for e in self.expenses.values() if self.can_see(user, e)]


def public_view(expense: dict) -> dict:
    return {k: expense[k] for k in PUBLIC_FIELDS}
