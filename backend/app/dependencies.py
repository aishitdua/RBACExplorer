from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models import Permission, Project, Resource, Role

CurrentUser = Annotated[str, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_session)]


async def get_project_for_user_or_404(
    slug: str, user_id: str, session: AsyncSession
) -> Project:
    project = await session.scalar(
        select(Project).where(Project.slug == slug, Project.owner_user_id == user_id)
    )
    if not project:
        raise HTTPException(404, "Project not found")
    return project


async def get_role_for_project_or_404(
    role_id: str, project_id: str, session: AsyncSession
) -> Role:
    role = await session.scalar(
        select(Role).where(Role.id == role_id, Role.project_id == project_id)
    )
    if not role:
        raise HTTPException(404, "Role not found")
    return role


async def get_permission_for_project_or_404(
    perm_id: str, project_id: str, session: AsyncSession
) -> Permission:
    perm = await session.scalar(
        select(Permission).where(
            Permission.id == perm_id, Permission.project_id == project_id
        )
    )
    if not perm:
        raise HTTPException(404, "Permission not found")
    return perm


async def get_resource_for_project_or_404(
    res_id: str, project_id: str, session: AsyncSession
) -> Resource:
    resource = await session.scalar(
        select(Resource).where(Resource.id == res_id, Resource.project_id == project_id)
    )
    if not resource:
        raise HTTPException(404, "Resource not found")
    return resource
