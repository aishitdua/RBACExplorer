from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Project, Resource

router = APIRouter(tags=["import"])

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete"}


@router.post("/projects/{slug}/import/openapi")
async def import_openapi(slug: str, body: dict, session: AsyncSession = Depends(get_session)):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")

    paths = body.get("paths", {})
    created = 0
    skipped = 0

    for path, methods in paths.items():
        for method in methods:
            if method.lower() not in SUPPORTED_METHODS:
                continue
            existing = await session.scalar(
                select(Resource).where(
                    Resource.project_id == project.id,
                    Resource.method == method.upper(),
                    Resource.path == path,
                )
            )
            if existing:
                skipped += 1
            else:
                session.add(Resource(project_id=project.id, method=method.upper(), path=path))
                created += 1

    await session.commit()
    return {"created": created, "skipped": skipped}
