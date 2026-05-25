from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.api.auth import router as auth_router
from app.api.universities import router as universities_router
from app.api.users import router as users_router
from app.api.items import router as items_router
from app.api.matches import router as matches_router
from app.api.notifications import router as notifications_router
from app.api.push import router as push_router
from app.api.verification import router as verification_router
from app.core.scheduler import scheduler_lifespan

settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="FAiND API",
    description="AI-powered lost and found platform for university campuses",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=scheduler_lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(universities_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(items_router, prefix="/api/v1")
app.include_router(matches_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(push_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Never expose stack traces in production."""
    if settings.DEBUG:
        raise exc
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )
