from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.database import get_session
from app.models import Project, Role, RoleInheritance, RolePermission
from app.schemas import RoleCreate, RoleUpdate, RoleOut, AddParentBody

router = APIRouter(tags=["roles"])


async def get_project_or_404(slug: str, session: AsyncSession) -> Project:
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")
    return project


async def get_role_or_404(role_id: str, project_id: str, session: AsyncSession) -> Role:
    role = await session.scalar(
        select(Role).where(Role.id == role_id, Role.project_id == project_id)
    )
    if not role:
        raise HTTPException(404, "Role not found")
    return role


async def would_create_cycle(child_id: str, parent_id: str, session: AsyncSession) -> bool:
    """
    Check if adding parent_id as a parent of child_id would create a cycle.
    A cycle exists if parent_id is already a descendant of child_id.
    We use a recursive CTE to find all descendants of child_id and check if
    parent_id is among them.
    """
    # SQLite supports recursive CTEs since 3.8.3
    sql = text("""
        WITH RECURSIVE descendants AS (
            SELECT :child_id AS id
            UNION ALL
            SELECT ri.child_role_id
            FROM role_inheritance ri
            JOIN descendants d ON ri.parent_role_id = d.id
        )
        SELECT COUNT(*) FROM descendants WHERE id = :parent_id
    """)
    result = await session.scalar(sql, {"child_id": child_id, "parent_id": parent_id})
    return (result or 0) > 0


@router.get("/projects/{slug}/roles", response_model=list[dict])
async def list_roles(slug: str, session: AsyncSession = Depends(get_session)):
    from sqlalchemy.orm import selectinload
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project: raise HTTPException(404)
    
    roles = await session.scalars(
        select(Role)
        .where(Role.project_id == project.id)
        .options(
            selectinload(Role.parent_links),
            selectinload(Role.permission_links).selectinload(RolePermission.permission)
        )
    )
    
    result = []
    for r in roles:
        result.append({
            "id": r.id,
            "name": r.name,
            "color": r.color,
            "parents": [link.parent_role_id for link in r.parent_links],
            "permissions": [
                {
                    "id": link.permission_id,
                    "name": link.permission.name,
                    "module": link.permission.name.split('.')[0] if '.' in link.permission.name else 'other'
                }
                for link in r.permission_links
            ]
        })
        
    return result


@router.post("/projects/{slug}/roles", response_model=RoleOut, status_code=201)
async def create_role(slug: str, body: RoleCreate, session: AsyncSession = Depends(get_session)):
    project = await get_project_or_404(slug, session)
    role = Role(project_id=project.id, name=body.name, description=body.description, color=body.color)
    session.add(role)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(400, "Role name already exists in this project")
    await session.refresh(role)
    return role


@router.patch("/projects/{slug}/roles/{role_id}", response_model=RoleOut)
async def update_role(
    slug: str, role_id: str, body: RoleUpdate, session: AsyncSession = Depends(get_session)
):
    project = await get_project_or_404(slug, session)
    role = await get_role_or_404(role_id, project.id, session)
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
        raise HTTPException(400, "Role name already exists in this project")
    await session.refresh(role)
    return role


@router.delete("/projects/{slug}/roles/{role_id}", status_code=204)
async def delete_role(slug: str, role_id: str, session: AsyncSession = Depends(get_session)):
    project = await get_project_or_404(slug, session)
    role = await get_role_or_404(role_id, project.id, session)
    await session.delete(role)
    await session.commit()


@router.post("/projects/{slug}/roles/{role_id}/parents", response_model=RoleOut)
async def add_parent(
    slug: str, role_id: str, body: AddParentBody, session: AsyncSession = Depends(get_session)
):
    project = await get_project_or_404(slug, session)
    child_role = await get_role_or_404(role_id, project.id, session)
    parent_role = await get_role_or_404(body.parent_role_id, project.id, session)

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
        raise HTTPException(400, "Adding this parent would create a cycle in the role hierarchy")

    inheritance = RoleInheritance(parent_role_id=parent_role.id, child_role_id=child_role.id)
    session.add(inheritance)
    await session.commit()
    return child_role


@router.delete("/projects/{slug}/roles/{role_id}/parents/{parent_id}", status_code=204)
async def remove_parent(
    slug: str, role_id: str, parent_id: str, session: AsyncSession = Depends(get_session)
):
    project = await get_project_or_404(slug, session)
    await get_role_or_404(role_id, project.id, session)
    await get_role_or_404(parent_id, project.id, session)

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
