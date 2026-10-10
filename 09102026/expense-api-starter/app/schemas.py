from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    food = "food"
    travel = "travel"
    bills = "bills"
    shopping = "shopping"
    other = "other"


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    category: Category = Category.other
    spent_on: date = Field(default_factory=date.today)


class Expense(ExpenseCreate):
    id: int


class Summary(BaseModel):
    count: int
    total: float
    by_category: dict[str, float]
