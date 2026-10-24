from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
from .routers import (
    health_router,
    auth_router,
    deals_router,
    invitations_router,
    conversations_router,
    clarifications_router,
    agreements_router,
    amendments_router,
    activity_router,
    notifications_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Legalbandu API: AI-powered platform converting informal business conversations into clear, mutually reviewed, confirmed, and version-controlled agreements.",
    lifespan=lifespan,
)

# CORS Configuration
allowed_origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Register API Routers
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(deals_router, prefix=settings.API_V1_PREFIX)
app.include_router(invitations_router, prefix=settings.API_V1_PREFIX)
app.include_router(conversations_router, prefix=settings.API_V1_PREFIX)
app.include_router(clarifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(agreements_router, prefix=settings.API_V1_PREFIX)
app.include_router(amendments_router, prefix=settings.API_V1_PREFIX)
app.include_router(activity_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "project": "Legalbandu",
        "tagline": "From Handshake to Contract",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
