"""STRETCH (DEV-17): GET /reports/daily-summary?travel_date=  — see spec 6.7 and the Test Contract."""
from fastapi import APIRouter, Depends

from app.core.deps import require_roles
from app.models import Role

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_roles(Role.ADMIN))])

# TODO (stretch): implement daily_summary
