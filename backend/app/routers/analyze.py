from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_session
from app.models import Project, Resource
from app.schemas import AnalyzeOut, ConflictFinding, DiffOut, SimulatedResource

router = APIRouter(tags=["analyze"])


@router.get("/projects/{slug}/analyze", response_model=AnalyzeOut)
async def analyze_project(slug: str, session: AsyncSession = Depends(get_session)):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")

    findings = []

    # 1. Orphaned permissions
    result = await session.execute(text("""
        SELECT p.id, p.name FROM permissions p
        WHERE p.project_id = :pid
        AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.permission_id = p.id)
    """), {"pid": project.id})
    for row in result.fetchall():
        findings.append(ConflictFinding(type="orphaned_permission", detail={"permission_id": row.id, "permission_name": row.name}))

    # 2. Empty roles (no permissions, no children)
    result = await session.execute(text("""
        SELECT r.id, r.name FROM roles r
        WHERE r.project_id = :pid
        AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id)
        AND NOT EXISTS (SELECT 1 FROM role_inheritance ri WHERE ri.parent_role_id = r.id)
    """), {"pid": project.id})
    for row in result.fetchall():
        findings.append(ConflictFinding(type="empty_role", detail={"role_id": row.id, "role_name": row.name}))

    # 3. Redundant assignments
    result = await session.execute(text("""
        WITH RECURSIVE ancestors AS (
            SELECT parent_role_id, child_role_id FROM role_inheritance
            UNION ALL
            SELECT ri.parent_role_id, a.child_role_id
            FROM role_inheritance ri JOIN ancestors a ON ri.child_role_id = a.parent_role_id
        )
        SELECT DISTINCT r.id AS role_id, r.name AS role_name, p.id AS perm_id, p.name AS perm_name
        FROM ancestors a
        JOIN role_permissions rp_child ON rp_child.role_id = a.child_role_id
        JOIN role_permissions rp_parent ON rp_parent.role_id = a.parent_role_id
            AND rp_parent.permission_id = rp_child.permission_id
        JOIN roles r ON r.id = a.child_role_id
        JOIN permissions p ON p.id = rp_child.permission_id
        WHERE r.project_id = :pid
    """), {"pid": project.id})
    for row in result.fetchall():
        findings.append(ConflictFinding(type="redundant_assignment", detail={"role_id": row.role_id, "role_name": row.role_name, "permission_id": row.perm_id, "permission_name": row.perm_name}))

    return AnalyzeOut(findings=findings)


@router.get("/projects/{slug}/diff/{role_id}", response_model=DiffOut)
async def diff_role(
    slug: str,
    role_id: str,
    add_permissions: list[str] = Query(default=[]),
    remove_permissions: list[str] = Query(default=[]),
    session: AsyncSession = Depends(get_session),
):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")

    async def resolve_allowed_resource_ids(extra_perm_ids: set, excluded_perm_ids: set) -> set:
        # Get current permissions via ancestor walk
        result = await session.execute(
            text("""
            WITH RECURSIVE role_ancestors AS (
                SELECT :role_id AS id
                UNION ALL
                SELECT ri.parent_role_id
                FROM role_inheritance ri
                JOIN role_ancestors ra ON ri.child_role_id = ra.id
            )
            SELECT DISTINCT rp.permission_id
            FROM role_permissions rp
            WHERE rp.role_id IN (SELECT id FROM role_ancestors)
            """),
            {"role_id": role_id},
        )
        current_perm_ids = {row[0] for row in result.fetchall()}
        effective_perm_ids = (current_perm_ids | extra_perm_ids) - excluded_perm_ids

        if not effective_perm_ids:
            return set()

        # Use ORM for the IN query (avoids SQLite binding issues)
        from sqlalchemy import select as sa_select
        from app.models import PermissionResource
        res_result = await session.execute(
            sa_select(PermissionResource.resource_id).where(
                PermissionResource.permission_id.in_(list(effective_perm_ids))
            )
        )
        return {row[0] for row in res_result.fetchall()}

    before_ids = await resolve_allowed_resource_ids(set(), set(remove_permissions))
    after_ids = await resolve_allowed_resource_ids(set(add_permissions), set(remove_permissions))

    all_resources_result = await session.execute(select(Resource).where(Resource.project_id == project.id))
    all_resources = {r.id: r for r in all_resources_result.scalars().all()}

    gained = [
        SimulatedResource(resource_id=rid, method=all_resources[rid].method, path=all_resources[rid].path, allowed=True)
        for rid in (after_ids - before_ids) if rid in all_resources
    ]
    lost = [
        SimulatedResource(resource_id=rid, method=all_resources[rid].method, path=all_resources[rid].path, allowed=False)
        for rid in (before_ids - after_ids) if rid in all_resources
    ]

    return DiffOut(
        role_id=role_id,
        gained=gained,
        lost=lost,
        unchanged_allowed=len(before_ids & after_ids),
        unchanged_denied=len(set(all_resources) - before_ids - after_ids),
    )
