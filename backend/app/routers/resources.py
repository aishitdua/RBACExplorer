import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import (
    CurrentUser,
    DBSession,
    get_project_for_user_or_404,
    get_resource_for_project_or_404,
)
from app.models import Resource
from app.schemas import ResourceCreate, ResourceOut, ResourceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["resources"])


@router.get("/projects/{slug}/resources", response_model=list[ResourceOut])
async def list_resources(slug: str, current_user: CurrentUser, session: DBSession):
    project = await get_project_for_user_or_404(slug, current_user, session)
    result = await session.execute(
        select(Resource).where(Resource.project_id == project.id)
    )
    return result.scalars().all()


@router.post("/projects/{slug}/resources", response_model=ResourceOut, status_code=201)
async def create_resource(
    slug: str, body: ResourceCreate, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
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
    current_user: CurrentUser,
    session: DBSession,
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    res = await get_resource_for_project_or_404(res_id, project.id, session)
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
    slug: str, res_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    res = await get_resource_for_project_or_404(res_id, project.id, session)
    await session.delete(res)
    await session.commit()
    logger.info("resource.deleted project=%s resource_id=%s", slug, res_id)
