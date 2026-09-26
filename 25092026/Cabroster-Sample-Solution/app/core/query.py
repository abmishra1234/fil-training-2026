import math
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def apply_sort(stmt, sort_by: str, order: str, allowed: dict, id_column):
    if sort_by not in allowed:
        raise HTTPException(422, detail=f"Invalid sort_by '{sort_by}'")
    col = allowed[sort_by]
    stmt = stmt.order_by(col.desc() if order == "desc" else col.asc())
    return stmt.order_by(id_column.asc())  # deterministic tie-break


def check_date_range(date_from, date_to):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, detail="date_from must be on or before date_to")


def paginate(db: Session, stmt, page: int, size: int, mapper: Callable[[Any], Any] = lambda x: x) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset((page - 1) * size).limit(size)).unique().all()
    return {
        "items": [mapper(r) for r in rows],
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if total else 0,
    }
