"""The V1 'master router' (Task 1).

Re-uses the existing routers under /api/v1 - no endpoint code is copied.
New resources (Tasks 3-4) are published ONLY here, so new features
nudge clients towards the versioned API.
"""
from fastapi import APIRouter

from ...routers.account_router import router as account_router
from ...routers.transaction_router import router as transaction_router            # Task 3
from ...routers.scheduled_payment_router import router as scheduled_payment_router  # Task 4

from ...routers.auth_router import router as auth_router                            # Ext 6
from ...routers.admin_router import router as admin_router                          # Ext 6

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)          # Ext 6: /api/v1/auth/...  (public: register, token)
router.include_router(admin_router)         # Ext 6: /api/v1/admin/... (ADMIN only)
router.include_router(account_router)
router.include_router(transaction_router)
router.include_router(scheduled_payment_router)
