from .health import router as health_router
from .auth_router import router as auth_router
from .deals import router as deals_router
from .invitations import router as invitations_router
from .conversations import router as conversations_router
from .clarifications import router as clarifications_router
from .agreements import router as agreements_router
from .amendments import router as amendments_router
from .activity import router as activity_router
from .notifications import router as notifications_router
from .bonds import router as bonds_router
from .compliance_router import router as compliance_router
from .assistance_router import router as assistance_router
from .lawyer_reviews import router as lawyer_reviews_router

__all__ = [
    "health_router",
    "auth_router",
    "deals_router",
    "invitations_router",
    "conversations_router",
    "clarifications_router",
    "agreements_router",
    "amendments_router",
    "activity_router",
    "notifications_router",
    "bonds_router",
    "compliance_router",
    "assistance_router",
    "lawyer_reviews_router",
]

