import csv
import io
import logging

import yaml
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from app.dependencies import CurrentUser, DBSession, get_project_for_user_or_404
from app.models import (
    Permission,
    PermissionResource,
    Resource,
    Role,
    RoleInheritance,
    RolePermission,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["import"])

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete"}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB limit

ALLOWED_CSV_TYPES = {"text/csv", "application/csv", "text/plain"}
ALLOWED_YAML_TYPES = {
    "text/yaml",
    "application/yaml",
    "application/x-yaml",
    "text/plain",
    "text/x-yaml",
}


CHUNK_SIZE = 64 * 1024  # 64KB read chunks


async def read_upload_with_limit(file: UploadFile, allowed_types: set[str]) -> bytes:
    if (
        file.content_type
        and file.content_type.split(";")[0].strip() not in allowed_types
    ):
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    data = b""
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        data += chunk
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(
                413,
                f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024}MB",
            )
    return data


@router.post("/projects/{slug}/import/openapi")
async def import_openapi(
    slug: str, body: dict, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)

    paths = body.get("paths", {})
    created = 0
    skipped = 0

    if len(paths) > 500:
        raise HTTPException(400, "Too many paths in OpenAPI spec (max 500)")

    for path, methods in paths.items():
        for method in methods:
            if method.lower() not in SUPPORTED_METHODS:
                continue
            existing = await session.scalar(
                select(Resource).where(
                    Resource.project_id == project.id,
                    Resource.method == method.upper(),
                    Resource.path == path,
                )
            )
            if existing:
                skipped += 1
            else:
                session.add(
                    Resource(project_id=project.id, method=method.upper(), path=path)
                )
                created += 1

    await session.commit()
    logger.info(
        "import.openapi project=%s created=%d skipped=%d", slug, created, skipped
    )
    return {"created": created, "skipped": skipped}


@router.post("/projects/{slug}/import/csv")
async def import_csv(
    slug: str,
    current_user: CurrentUser,
    session: DBSession,
    file: UploadFile = File(...),
):
    content = await read_upload_with_limit(file, ALLOWED_CSV_TYPES)
    project = await get_project_for_user_or_404(slug, current_user, session)

    string_content = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(string_content))

    created = 0
    skipped = 0
    count = 0
    for row in reader:
        count += 1
        if count > 1000:
            break

        method = row.get("method", "").upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            continue

        path = row.get("path", "")
        desc = row.get("description", "")

        if not method or not path:
            continue

        existing = await session.scalar(
            select(Resource).where(
                Resource.project_id == project.id,
                Resource.method == method,
                Resource.path == path,
            )
        )
        if existing:
            skipped += 1
        else:
            session.add(
                Resource(
                    project_id=project.id, method=method, path=path, description=desc
                )
            )
            created += 1

    await session.commit()
    logger.info("import.csv project=%s created=%d skipped=%d", slug, created, skipped)
    return {"created": created, "skipped": skipped, "processed": count}


@router.post("/projects/{slug}/import/yaml")
async def import_yaml(
    slug: str,
    current_user: CurrentUser,
    session: DBSession,
    file: UploadFile = File(...),
):
    project = await get_project_for_user_or_404(slug, current_user, session)

    try:
        content = await read_upload_with_limit(file, ALLOWED_YAML_TYPES)
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError("YAML root must be a dictionary of roles")

        # Helper to guess HTTP method
        def guess_method(action: str) -> str:
            a = str(action).lower()
            if any(
                w in a
                for w in [
                    "index",
                    "show",
                    "search",
                    "fetch",
                    "list",
                    "get",
                    "results",
                    "summary",
                    "stats",
                    "preview",
                    "details",
                    "events",
                ]
            ):
                return "GET"
            if any(
                w in a
                for w in [
                    "destroy",
                    "delete",
                    "remove",
                    "void",
                    "purge",
                    "block",
                    "inactivate",
                    "deactivate",
                ]
            ):
                return "DELETE"
            if any(
                w in a
                for w in [
                    "update",
                    "edit",
                    "set",
                    "toggle",
                    "change",
                    "reset",
                    "fix",
                    "mark",
                    "pass",
                    "fail",
                    "approve",
                    "reject",
                    "deny",
                    "escalate",
                    "revoke",
                    "grant",
                    "transfer",
                ]
            ):
                return "PUT"
            return "POST"

        # Helper to generate a consistent color based on name
        def generate_color(name: str) -> str:
            colors = [
                "#3b82f6",
                "#ef4444",
                "#10b981",
                "#f59e0b",
                "#8b5cf6",
                "#ec4899",
                "#06b6d4",
                "#84cc16",
                "#6366f1",
                "#f97316",
            ]
            # Simple hash to pick a color
            idx = sum(ord(c) for c in name) % len(colors)
            return colors[idx]

        role_map = {}  # name -> id

        # Helper to get or create role by name
        async def ensure_role(name: str) -> str:
            if not name or not isinstance(name, str):
                return None
            if name in role_map:
                return role_map[name]
            role = await session.scalar(
                select(Role).where(Role.project_id == project.id, Role.name == name)
            )
            if not role:
                role = Role(
                    project_id=project.id, name=name, color=generate_color(name)
                )
                session.add(role)
                await session.flush()
            role_map[name] = role.id
            return role.id

        # First pass: Scan all keys AND all includes to ensure roles exist
        for role_name, modules in data.items():
            await ensure_role(role_name)
            if isinstance(modules, dict) and "include" in modules:
                includes = modules["include"]
                if isinstance(includes, list):
                    for parent_name in includes:
                        await ensure_role(parent_name)

        # Second pass: Process permissions and resources
        for role_name, modules in data.items():
            if not role_name or not isinstance(modules, dict):
                continue

            role_id = role_map[role_name]

            for module_name, actions in modules.items():
                if module_name == "include":
                    if not isinstance(actions, list):
                        continue
                    for parent_name in actions:
                        if parent_name in role_map:
                            parent_id = role_map[parent_name]
                            link = await session.scalar(
                                select(RoleInheritance).where(
                                    RoleInheritance.parent_role_id == parent_id,
                                    RoleInheritance.child_role_id == role_id,
                                )
                            )
                            if not link:
                                session.add(
                                    RoleInheritance(
                                        parent_role_id=parent_id, child_role_id=role_id
                                    )
                                )
                    continue

                if not isinstance(actions, dict):
                    continue

                for action_name, description in actions.items():
                    if not action_name:
                        continue
                    perm_name = f"{module_name}.{action_name}"

                    # Create Permission
                    perm = await session.scalar(
                        select(Permission).where(
                            Permission.project_id == project.id,
                            Permission.name == perm_name,
                        )
                    )
                    if not perm:
                        perm = Permission(
                            project_id=project.id,
                            name=perm_name,
                            description=str(description),
                        )
                        session.add(perm)
                        await session.flush()

                    # Assign to Role
                    link = await session.scalar(
                        select(RolePermission).where(
                            RolePermission.role_id == role_id,
                            RolePermission.permission_id == perm.id,
                        )
                    )
                    if not link:
                        session.add(
                            RolePermission(role_id=role_id, permission_id=perm.id)
                        )

                    # Resource Mapping
                    method = guess_method(action_name)
                    path = f"/api/v1/{module_name}/{action_name}"

                    res = await session.scalar(
                        select(Resource).where(
                            Resource.project_id == project.id,
                            Resource.method == method,
                            Resource.path == path,
                        )
                    )
                    if not res:
                        res = Resource(
                            project_id=project.id,
                            method=method,
                            path=path,
                            description=str(description),
                        )
                        session.add(res)
                        await session.flush()

                    # Link Permission to Resource
                    p_res_link = await session.scalar(
                        select(PermissionResource).where(
                            PermissionResource.permission_id == perm.id,
                            PermissionResource.resource_id == res.id,
                        )
                    )
                    if not p_res_link:
                        session.add(
                            PermissionResource(
                                permission_id=perm.id, resource_id=res.id
                            )
                        )

        await session.commit()
        logger.info("import.yaml project=%s roles=%d", slug, len(role_map))
        return {"status": "success", "count": len(role_map)}
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        logger.exception("YAML import failed for project %s", slug)
        raise HTTPException(
            status_code=500,
            detail="Import failed. Check your YAML structure and try again.",
        ) from None
