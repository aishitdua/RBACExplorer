from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import (
    Permission,
    PermissionResource,
    Project,
    RolePermission,
)
from app.schemas import PermissionCreate, PermissionOut, PermissionUpdate

router = APIRouter(tags=["permissions"])


async def _get_project(slug: str, session: AsyncSession) -> Project:
    p = await session.scalar(select(Project).where(Project.slug == slug))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/projects/{slug}/permissions", response_model=list[PermissionOut])
async def list_permissions(slug: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    result = await session.execute(
        select(Permission).where(Permission.project_id == project.id)
    )
    return result.scalars().all()


@router.post(
    "/projects/{slug}/permissions", response_model=PermissionOut, status_code=201
)
async def create_permission(
    slug: str, body: PermissionCreate, session: AsyncSession = Depends(get_session)
):
    project = await _get_project(slug, session)
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
    return perm


@router.patch("/projects/{slug}/permissions/{perm_id}", response_model=PermissionOut)
async def update_permission(
    slug: str,
    perm_id: str,
    body: PermissionUpdate,
    session: AsyncSession = Depends(get_session),
):
    project = await _get_project(slug, session)
    perm = await session.scalar(
        select(Permission).where(
            Permission.id == perm_id, Permission.project_id == project.id
        )
    )
    if not perm:
        raise HTTPException(404, "Permission not found")
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
    return perm


@router.delete("/projects/{slug}/permissions/{perm_id}", status_code=204)
async def delete_permission(
    slug: str, perm_id: str, session: AsyncSession = Depends(get_session)
):
    project = await _get_project(slug, session)
    perm = await session.scalar(
        select(Permission).where(
            Permission.id == perm_id, Permission.project_id == project.id
        )
    )
    if not perm:
        raise HTTPException(404, "Permission not found")
    await session.delete(perm)
    await session.commit()


@router.post("/projects/{slug}/roles/{role_id}/permissions/{perm_id}")
async def assign_permission(
    slug: str, role_id: str, perm_id: str, session: AsyncSession = Depends(get_session)
):
    existing = await session.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == perm_id
        )
    )
    if not existing:
        session.add(RolePermission(role_id=role_id, permission_id=perm_id))
        await session.commit()
    return {"ok": True}


@router.delete(
    "/projects/{slug}/roles/{role_id}/permissions/{perm_id}", status_code=204
)
async def unassign_permission(
    slug: str, role_id: str, perm_id: str, session: AsyncSession = Depends(get_session)
):
    link = await session.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role_id, RolePermission.permission_id == perm_id
        )
    )
    if link:
        await session.delete(link)
        await session.commit()


@router.post("/projects/{slug}/permissions/{perm_id}/resources/{res_id}")
async def map_resource(
    slug: str, perm_id: str, res_id: str, session: AsyncSession = Depends(get_session)
):
    existing = await session.scalar(
        select(PermissionResource).where(
            PermissionResource.permission_id == perm_id,
            PermissionResource.resource_id == res_id,
        )
    )
    if not existing:
        session.add(PermissionResource(permission_id=perm_id, resource_id=res_id))
        await session.commit()
    return {"ok": True}


@router.delete(
    "/projects/{slug}/permissions/{perm_id}/resources/{res_id}", status_code=204
)
async def unmap_resource(
    slug: str, perm_id: str, res_id: str, session: AsyncSession = Depends(get_session)
):
    link = await session.scalar(
        select(PermissionResource).where(
            PermissionResource.permission_id == perm_id,
            PermissionResource.resource_id == res_id,
        )
    )
    if link:
        await session.delete(link)
        await session.commit()
