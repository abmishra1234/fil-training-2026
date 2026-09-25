"""Reusable list helpers (DEV-06). Every list endpoint must use these."""
import math  # noqa: F401

from fastapi import HTTPException  # noqa: F401
from sqlalchemy import func, select  # noqa: F401
from sqlalchemy.orm import Session


def apply_sort(stmt, sort_by: str, order: str, allowed: dict, id_column):
    """TODO: order stmt by allowed[sort_by] asc/desc, THEN by id_column asc (tie-break).
    Unknown sort_by -> HTTPException(422)."""
    raise NotImplementedError("DEV-06 apply_sort")


def check_date_range(date_from, date_to):
    """TODO: date_from > date_to -> HTTPException(422)."""
    raise NotImplementedError("DEV-06 check_date_range")


def paginate(db: Session, stmt, page: int, size: int, mapper=lambda x: x) -> dict:
    """TODO: return {"items", "total", "page", "size", "pages"}.
    total counts ALL filtered rows; pages = ceil(total/size) (0 when total is 0)."""
    raise NotImplementedError("DEV-06 paginate")
