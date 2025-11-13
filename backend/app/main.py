from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.endpoints import (
    auth,
    courses,
    content,
    assessments,
    enrollments,
    payments,
    analytics,
    proctoring,
    tracking,
    users,
    certificates,
)


def get_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register health endpoint
    @app.get("/health", tags=["health"])
    def health_check() -> dict:
        return {"status": "ok"}

    # API v1 routers
    api_router = APIRouter(prefix=settings.API_V1_PREFIX)

    api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
    api_router.include_router(users.router, prefix="/users", tags=["users"])
    api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
    api_router.include_router(content.router, prefix="/content", tags=["content"])
    api_router.include_router(assessments.router, prefix="/assessments", tags=["assessments"])
    api_router.include_router(enrollments.router, prefix="/enrollments", tags=["enrollments"])
    api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
    api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
    api_router.include_router(proctoring.router, prefix="/proctoring", tags=["proctoring"])
    api_router.include_router(tracking.router, prefix="/tracking", tags=["tracking"])
    api_router.include_router(certificates.router, prefix="/certificates", tags=["certificates"])

    app.include_router(api_router)

    return app


app = get_application()

