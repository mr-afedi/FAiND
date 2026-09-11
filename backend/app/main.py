from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.scheduler import scheduler_lifespan
from app.api.auth import router as auth_router
from app.api.universities import router as universities_router
from app.api.users import router as users_router
from app.api.items import router as items_router
from app.api.matches import router as matches_router
from app.api.notifications import router as notifications_router
from app.api.push import router as push_router
from app.api.returns import router as returns_router
from app.api.reports import router as reports_router
from app.api.admin_reports import router as admin_reports_router
from app.api.drop_points import router as drop_points_router
from app.api.drop_off import router as drop_off_router
from app.api.tokens import router as tokens_router
from app.api.handover import router as handover_router
from app.api.claims import router as claims_router
from app.api.authority import router as authority_router
from app.api.admin_dashboard import router as admin_dashboard_router
from app.api.supervisor import router as supervisor_router

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

# CORS — in dev, allow LAN origins so phones on the same Wi‑Fi can reach the API
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=(
            r"https?://("
            r"localhost|127\.0\.0\.1"
            r"|192\.168\.\d{1,3}\.\d{1,3}"
            r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
            r")(:\d+)?"
        ),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
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
app.include_router(returns_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(admin_reports_router, prefix="/api/v1")
app.include_router(drop_points_router, prefix="/api/v1")
app.include_router(drop_off_router, prefix="/api/v1")
app.include_router(tokens_router, prefix="/api/v1")
app.include_router(handover_router, prefix="/api/v1")
app.include_router(claims_router, prefix="/api/v1")
app.include_router(authority_router, prefix="/api/v1")
app.include_router(admin_dashboard_router, prefix="/api/v1")
app.include_router(supervisor_router, prefix="/api/v1")


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
