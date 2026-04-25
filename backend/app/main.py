from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="RBACExplorer API", version="1.0.0")

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
