import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import settings
from app.routers import (
    analyze,
    export,
    import_,
    permissions,
    projects,
    resources,
    roles,
    simulate,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def _parse_cors_origins(raw: str) -> list[str]:
    if raw.strip() == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


cors_origins = _parse_cors_origins(settings.cors_origins)

app = FastAPI(title="RBACExplorer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=len(cors_origins) > 0 and cors_origins != ["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
app.include_router(simulate.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(import_.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
