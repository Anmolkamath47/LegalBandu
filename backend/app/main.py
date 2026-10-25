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
    bonds_router,
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
allowed_origins = [orig.strip() for orig in settings.FRONTEND_URL.split(",") if orig.strip()]
for default_orig in ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]:
    if default_orig not in allowed_origins:
        allowed_origins.append(default_orig)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
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
app.include_router(bonds_router, prefix=settings.API_V1_PREFIX)


import os
from fastapi.responses import FileResponse
from fastapi import HTTPException
from .services.audio_service import UPLOAD_DIR as AUDIO_UPLOAD_DIR
from .services.image_service import UPLOAD_DIR as IMAGE_UPLOAD_DIR


@app.get("/api/audio/{filename}")
def serve_audio_file(filename: str):
    file_path = os.path.join(AUDIO_UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(file_path)


@app.get("/api/images/{filename}")
def serve_image_file(filename: str):
    file_path = os.path.join(IMAGE_UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file not found.")
    return FileResponse(file_path)


@app.get("/")
def root():
    return {
        "project": "Legalbandu",
        "tagline": "From Handshake to Contract",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }

