import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import (
    CurrentUser,
    DBSession,
    get_permission_for_project_or_404,
    get_project_for_user_or_404,
    get_resource_for_project_or_404,
    get_role_for_project_or_404,
)
from app.models import (
    Permission,
    PermissionResource,
    RolePermission,
)
from app.schemas import PermissionCreate, PermissionOut, PermissionUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["permissions"])


@router.get("/projects/{slug}/permissions", response_model=list[PermissionOut])
async def list_permissions(slug: str, current_user: CurrentUser, session: DBSession):
    project = await get_project_for_user_or_404(slug, current_user, session)
    result = await session.execute(
        select(Permission).where(Permission.project_id == project.id)
    )
    return result.scalars().all()


@router.post(
    "/projects/{slug}/permissions", response_model=PermissionOut, status_code=201
)
async def create_permission(
    slug: str, body: PermissionCreate, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    perm = Permission(
        project_id=project.id, name=body.name, description=body.description
    )
    session.add(perm)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            400, "Permission name already exists in this project"
        ) from None
    await session.refresh(perm)
    logger.info("permission.created project=%s name=%s id=%s", slug, perm.name, perm.id)
    return perm


@router.patch("/projects/{slug}/permissions/{perm_id}", response_model=PermissionOut)
async def update_permission(
    slug: str,
    perm_id: str,
    body: PermissionUpdate,
    current_user: CurrentUser,
    session: DBSession,
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    perm = await get_permission_for_project_or_404(perm_id, project.id, session)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(perm, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            400, "Permission name already exists in this project"
        ) from None
    await session.refresh(perm)
    logger.info("permission.updated project=%s name=%s id=%s", slug, perm.name, perm.id)
    return perm


@router.delete("/projects/{slug}/permissions/{perm_id}", status_code=204)
async def delete_permission(
    slug: str, perm_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    perm = await get_permission_for_project_or_404(perm_id, project.id, session)
    await session.delete(perm)
    await session.commit()
    logger.info("permission.deleted project=%s perm_id=%s", slug, perm_id)


@router.post("/projects/{slug}/roles/{role_id}/permissions/{perm_id}")
async def assign_permission(
    slug: str, role_id: str, perm_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    await get_role_for_project_or_404(role_id, project.id, session)
    await get_permission_for_project_or_404(perm_id, project.id, session)
    existing = await session.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == perm_id
        )
    )
    if not existing:
        session.add(RolePermission(role_id=role_id, permission_id=perm_id))
        await session.commit()
        logger.info(
            "permission.assigned project=%s role=%s perm=%s", slug, role_id, perm_id
        )
    return {"ok": True}


@router.delete(
    "/projects/{slug}/roles/{role_id}/permissions/{perm_id}", status_code=204
)
async def unassign_permission(
    slug: str, role_id: str, perm_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    await get_role_for_project_or_404(role_id, project.id, session)
    await get_permission_for_project_or_404(perm_id, project.id, session)
    link = await session.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == perm_id
        )
    )
    if link:
        await session.delete(link)
        await session.commit()
        logger.info(
            "permission.unassigned project=%s role=%s perm=%s", slug, role_id, perm_id
        )


@router.post("/projects/{slug}/permissions/{perm_id}/resources/{res_id}")
async def map_resource(
    slug: str, perm_id: str, res_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    await get_permission_for_project_or_404(perm_id, project.id, session)
    await get_resource_for_project_or_404(res_id, project.id, session)
    existing = await session.scalar(
        select(PermissionResource).where(
            PermissionResource.permission_id == perm_id,
            PermissionResource.resource_id == res_id,
        )
    )
    if not existing:
        session.add(PermissionResource(permission_id=perm_id, resource_id=res_id))
        await session.commit()
        logger.info(
            "permission.resource_mapped project=%s perm=%s resource=%s",
            slug,
            perm_id,
            res_id,
        )
    return {"ok": True}


@router.delete(
    "/projects/{slug}/permissions/{perm_id}/resources/{res_id}", status_code=204
)
async def unmap_resource(
    slug: str, perm_id: str, res_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    await get_permission_for_project_or_404(perm_id, project.id, session)
    await get_resource_for_project_or_404(res_id, project.id, session)
    link = await session.scalar(
        select(PermissionResource).where(
            PermissionResource.permission_id == perm_id,
            PermissionResource.resource_id == res_id,
        )
    )
    if link:
        await session.delete(link)
        await session.commit()
        logger.info(
            "permission.resource_unmapped project=%s perm=%s resource=%s",
            slug,
            perm_id,
            res_id,
        )
