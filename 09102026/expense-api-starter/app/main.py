"""Expense API: a small FastAPI service we package with Docker."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from . import db
from .schemas import Category, Expense, ExpenseCreate, Summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()  # create the SQLite table on startup
    yield


app = FastAPI(title="Expense API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/expenses", response_model=Expense, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate) -> Expense:
    return db.add_expense(payload)


@app.get("/expenses", response_model=list[Expense])
def list_expenses(category: Category | None = None) -> list[Expense]:
    return db.list_expenses(category)


@app.get("/expenses/summary", response_model=Summary)
def summary() -> Summary:
    return db.summary()


@app.get("/expenses/{expense_id}", response_model=Expense)
def get_expense(expense_id: int) -> Expense:
    expense = db.get_expense(expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@app.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int) -> None:
    if not db.delete_expense(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
