import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Project, Resource
from app.schemas import ResourceCreate, ResourceOut, ResourceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resources"])


async def _get_project(slug: str, session: AsyncSession) -> Project:
    p = await session.scalar(select(Project).where(Project.slug == slug))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/projects/{slug}/resources", response_model=list[ResourceOut])
async def list_resources(slug: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    result = await session.execute(
        select(Resource).where(Resource.project_id == project.id)
    )
    return result.scalars().all()


@router.post("/projects/{slug}/resources", response_model=ResourceOut, status_code=201)
async def create_resource(
    slug: str, body: ResourceCreate, session: AsyncSession = Depends(get_session)
):
    project = await _get_project(slug, session)
    res = Resource(
        project_id=project.id,
        method=body.method.upper(),
        path=body.path,
        description=body.description,
    )
    session.add(res)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(400, "Resource already exists in this project") from None
    await session.refresh(res)
    logger.info(
        "resource.created project=%s method=%s path=%s id=%s",
        slug,
        res.method,
        res.path,
        res.id,
    )
    return res


@router.patch("/projects/{slug}/resources/{res_id}", response_model=ResourceOut)
async def update_resource(
    slug: str,
    res_id: str,
    body: ResourceUpdate,
    session: AsyncSession = Depends(get_session),
):
    project = await _get_project(slug, session)
    res = await session.scalar(
        select(Resource).where(Resource.id == res_id, Resource.project_id == project.id)
    )
    if not res:
        raise HTTPException(404, "Resource not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(res, field, value.upper() if field == "method" else value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(400, "Resource already exists in this project") from None
    await session.refresh(res)
    return res


@router.delete("/projects/{slug}/resources/{res_id}", status_code=204)
async def delete_resource(
    slug: str, res_id: str, session: AsyncSession = Depends(get_session)
):
    project = await _get_project(slug, session)
    res = await session.scalar(
        select(Resource).where(Resource.id == res_id, Resource.project_id == project.id)
    )
    if not res:
        raise HTTPException(404, "Resource not found")
    await session.delete(res)
    await session.commit()
    logger.info("resource.deleted project=%s resource_id=%s", slug, res_id)
