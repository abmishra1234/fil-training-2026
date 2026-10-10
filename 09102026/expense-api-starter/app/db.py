"""SQLite storage. The file path comes from EXPENSE_DB_PATH so Docker can put it on a volume."""
import os
import sqlite3
from pathlib import Path

from .schemas import Category, Expense, ExpenseCreate, Summary


def _db_path() -> Path:
    return Path(os.getenv("EXPENSE_DB_PATH", "data/expenses.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    _db_path().parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   amount REAL NOT NULL,
                   category TEXT NOT NULL,
                   spent_on TEXT NOT NULL)"""
        )


def _to_expense(row: sqlite3.Row) -> Expense:
    return Expense(**dict(row))


def add_expense(data: ExpenseCreate) -> Expense:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (title, amount, category, spent_on) VALUES (?, ?, ?, ?)",
            (data.title, data.amount, data.category.value, data.spent_on.isoformat()),
        )
        return Expense(id=cur.lastrowid, **data.model_dump())


def list_expenses(category: Category | None = None) -> list[Expense]:
    sql, args = "SELECT * FROM expenses", ()
    if category is not None:
        sql, args = sql + " WHERE category = ?", (category.value,)
    with _connect() as conn:
        return [_to_expense(r) for r in conn.execute(sql + " ORDER BY id", args)]


def get_expense(expense_id: int) -> Expense | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    return _to_expense(row) if row else None


def delete_expense(expense_id: int) -> bool:
    with _connect() as conn:
        return conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,)).rowcount > 0


def summary() -> Summary:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT category, COUNT(*) AS n, SUM(amount) AS total FROM expenses GROUP BY category"
        ).fetchall()
    by_category = {r["category"]: round(r["total"], 2) for r in rows}
    return Summary(
        count=sum(r["n"] for r in rows),
        total=round(sum(by_category.values()), 2),
        by_category=by_category,
    )
