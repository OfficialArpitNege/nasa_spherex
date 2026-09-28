from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.api.cutout import router as cutout_router
from app.api.motion import router as motion_router
from app.api.known_objects import router as known_objects_router
from app.api.hypothesis import router as hypothesis_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SPHEREx Moving Object Explorer Backend API"
)

# Centralized CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(search_router, prefix=settings.API_V1_STR, tags=["Search"])
app.include_router(cutout_router, prefix=settings.API_V1_STR, tags=["Cutout"])
app.include_router(motion_router, prefix=settings.API_V1_STR, tags=["Motion Analysis"])
app.include_router(known_objects_router, prefix=settings.API_V1_STR, tags=["Known Objects"])
app.include_router(hypothesis_router, prefix=settings.API_V1_STR, tags=["Hypothesis Update"])

@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
