from .auth import router as auth_router
from .detect import router as detect_router
from .notifications import router as notifications_router

__all__ = ["auth_router", "detect_router", "notifications_router"]
