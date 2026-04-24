from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_session
from app.models import Project
from app.schemas import AnalyzeOut, ConflictFinding

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
