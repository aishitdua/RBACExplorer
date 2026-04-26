from fastapi import APIRouter, HTTPException
from sqlalchemy import select, text

from app.dependencies import CurrentUser, DBSession, get_project_for_user_or_404
from app.models import Resource, Role
from app.schemas import SimulatedResource, SimulateOut

router = APIRouter(tags=["simulate"])


@router.get("/projects/{slug}/simulate/{role_id}", response_model=SimulateOut)
async def simulate_role(
    slug: str, role_id: str, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    role = await session.scalar(
        select(Role).where(Role.id == role_id, Role.project_id == project.id)
    )
    if not role:
        raise HTTPException(404, "Role not found")

    # Recursive CTE: collect all ancestor role IDs including the role itself
    allowed_result = await session.execute(
        text("""
        WITH RECURSIVE role_ancestors AS (
            SELECT :role_id AS id
            UNION ALL
            SELECT ri.parent_role_id
            FROM role_inheritance ri
            JOIN role_ancestors ra ON ri.child_role_id = ra.id
        )
        SELECT DISTINCT
            res.id AS resource_id,
            res.method,
            res.path,
            p.name AS permission_name,
            r.name AS role_name
        FROM resources res
        JOIN permission_resources pr ON pr.resource_id = res.id
        JOIN permissions p ON p.id = pr.permission_id
        JOIN role_permissions rp ON rp.permission_id = p.id
        JOIN roles r ON r.id = rp.role_id
        WHERE rp.role_id IN (SELECT id FROM role_ancestors)
        AND res.project_id = :project_id
        """),
        {"role_id": role_id, "project_id": project.id},
    )
    allowed_rows = allowed_result.fetchall()
    allowed_ids = {row.resource_id for row in allowed_rows}
    allowed_map = {row.resource_id: row for row in allowed_rows}

    all_resources_result = await session.execute(
        select(Resource).where(Resource.project_id == project.id)
    )
    all_resources = all_resources_result.scalars().all()

    simulated = []
    for res in all_resources:
        if res.id in allowed_ids:
            row = allowed_map[res.id]
            simulated.append(
                SimulatedResource(
                    resource_id=res.id,
                    method=res.method,
                    path=res.path,
                    allowed=True,
                    granted_by_permission=row.permission_name,
                    granted_by_role=row.role_name,
                )
            )
        else:
            simulated.append(
                SimulatedResource(
                    resource_id=res.id,
                    method=res.method,
                    path=res.path,
                    allowed=False,
                )
            )

    return SimulateOut(role_id=role_id, role_name=role.name, resources=simulated)
