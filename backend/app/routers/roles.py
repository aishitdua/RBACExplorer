import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    CurrentUser,
    DBSession,
    get_project_for_user_or_404,
    get_role_for_project_or_404,
)
from app.models import Role, RoleInheritance, RolePermission
from app.schemas import AddParentBody, RoleCreate, RoleOut, RoleUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["roles"])

MAX_INHERITANCE_DEPTH = 32


async def would_create_cycle(
    child_id: str, parent_id: str, session: AsyncSession
) -> bool:
    """
    Check if adding parent_id as a parent of child_id would create a cycle.
    A cycle exists if parent_id is already a descendant of child_id.
    We use a recursive CTE to find all descendants of child_id and check if
    parent_id is among them.
    """
    # SQLite supports recursive CTEs since 3.8.3
    sql = text(f"""
        WITH RECURSIVE descendants AS (
            SELECT :child_id AS id, 0 AS depth
            UNION ALL
            SELECT ri.child_role_id, d.depth + 1
            FROM role_inheritance ri
            JOIN descendants d ON ri.parent_role_id = d.id
            WHERE d.depth < {MAX_INHERITANCE_DEPTH}
        )
        SELECT COUNT(*) FROM descendants WHERE id = :parent_id
    """)
    result = await session.scalar(sql, {"child_id": child_id, "parent_id": parent_id})
    return (result or 0) > 0


@router.get("/projects/{slug}/roles", response_model=list[dict])
async def list_roles(slug: str, current_user: CurrentUser, session: DBSession):
    from sqlalchemy.orm import selectinload

    project = await get_project_for_user_or_404(slug, current_user, session)

    roles = await session.scalars(
        select(Role)
        .where(Role.project_id == project.id)
        .options(
            selectinload(Role.parent_links),
            selectinload(Role.permission_links).selectinload(RolePermission.permission),
        )
    )

    result = []
    for r in roles:
        result.append(
            {
                "id": r.id,
                "name": r.name,
                "color": r.color,
                "parents": [link.parent_role_id for link in r.parent_links],
                "permissions": [
                    {
                        "id": link.permission_id,
                        "name": link.permission.name,
                        "module": link.permission.name.split(".")[0]
                        if "." in link.permission.name
                        else "other",
                    }
                    for link in r.permission_links
                ],
            }
        )

    return result


@router.post("/projects/{slug}/roles", response_model=RoleOut, status_code=201)
async def create_role(
    slug: str, body: RoleCreate, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    role = Role(
        project_id=project.id,
        name=body.name,
        description=body.description,
        color=body.color,
    )
    session.add(role)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(400, "Role name already exists in this project") from None
    await session.refresh(role)
    logger.info("role.created project=%s role=%s id=%s", slug, role.name, role.id)
    return role


@router.patch("/projects/{slug}/roles/{role_id}", response_model=RoleOut)
async def update_role(
    slug: str,
    role_id: str,
    body: RoleUpdate,
    current_user: CurrentUser,
    session: DBSession,
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    role = await get_role_for_project_or_404(role_id, project.id, session)
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    if body.color is not None:
        role.color = body.color
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(400, "Role name already exists in this project") from None
    await session.refresh(role)
    logger.info("role.updated project=%s role=%s id=%s", slug, role.name, role.id)
    return role


@router.delete("/projects/{slug}/roles/{role_id}", status_code=204)
async def delete_role(
    slug: str, role_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    role = await get_role_for_project_or_404(role_id, project.id, session)
    await session.delete(role)
    await session.commit()
    logger.info("role.deleted project=%s role_id=%s", slug, role_id)


@router.post("/projects/{slug}/roles/{role_id}/parents", response_model=RoleOut)
async def add_parent(
    slug: str,
    role_id: str,
    body: AddParentBody,
    current_user: CurrentUser,
    session: DBSession,
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    child_role = await get_role_for_project_or_404(role_id, project.id, session)
    parent_role = await get_role_for_project_or_404(
        body.parent_role_id, project.id, session
    )

    if child_role.id == parent_role.id:
        raise HTTPException(400, "A role cannot inherit from itself")

    # Check if relationship already exists
    existing = await session.scalar(
        select(RoleInheritance).where(
            RoleInheritance.parent_role_id == parent_role.id,
            RoleInheritance.child_role_id == child_role.id,
        )
    )
    if existing:
        return child_role

    # Cycle detection: would adding parent_role as parent of child_role create a cycle?
    if await would_create_cycle(child_role.id, parent_role.id, session):
        raise HTTPException(
            400, "Adding this parent would create a cycle in the role hierarchy"
        )

    inheritance = RoleInheritance(
        parent_role_id=parent_role.id, child_role_id=child_role.id
    )
    session.add(inheritance)
    await session.commit()
    logger.info(
        "role.parent_added project=%s child=%s parent=%s",
        slug,
        role_id,
        body.parent_role_id,
    )
    return child_role


@router.delete("/projects/{slug}/roles/{role_id}/parents/{parent_id}", status_code=204)
async def remove_parent(
    slug: str,
    role_id: str,
    parent_id: str,
    current_user: CurrentUser,
    session: DBSession,
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    await get_role_for_project_or_404(role_id, project.id, session)
    await get_role_for_project_or_404(parent_id, project.id, session)

    link = await session.scalar(
        select(RoleInheritance).where(
            RoleInheritance.parent_role_id == parent_id,
            RoleInheritance.child_role_id == role_id,
        )
    )
    if not link:
        raise HTTPException(404, "Parent relationship not found")
    await session.delete(link)
    await session.commit()
    logger.info(
        "role.parent_removed project=%s child=%s parent=%s", slug, role_id, parent_id
    )
