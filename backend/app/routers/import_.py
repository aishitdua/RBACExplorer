import csv
import io
import logging
from collections import defaultdict

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


def _has_cycle(edges: list[tuple[str, str]]) -> bool:
    """Check if the directed graph formed by (parent_id, child_id) edges has a cycle."""
    children = defaultdict(set)
    for parent, child in edges:
        children[parent].add(child)

    def dfs(node, visited, stack):
        visited.add(node)
        stack.add(node)
        for neighbor in children.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor, visited, stack):
                    return True
            elif neighbor in stack:
                return True
        stack.discard(node)
        return False

    all_nodes = set(children.keys()) | {c for s in children.values() for c in s}
    visited = set()
    for node in all_nodes:
        if node not in visited:
            if dfs(node, visited, set()):
                return True
    return False


@router.post("/projects/{slug}/import/openapi")
async def import_openapi(
    slug: str, body: dict, current_user: CurrentUser, session: DBSession
):
    project = await get_project_for_user_or_404(slug, current_user, session)

    paths = body.get("paths", {})
    created = 0
    skipped = 0

    if not isinstance(paths, dict):
        raise HTTPException(400, "Invalid OpenAPI spec: 'paths' must be an object")

    if len(paths) > 500:
        raise HTTPException(400, "Too many paths in OpenAPI spec (max 500)")

    for path, methods in paths.items():
        if not isinstance(path, str) or not path.startswith("/"):
            skipped += 1
            continue

        if not isinstance(methods, dict):
            skipped += 1
            continue

        method_keys = list(methods.keys())
        if len(method_keys) > 20:
            method_keys = method_keys[:20]
            skipped += len(methods) - 20

        for method in method_keys:
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
    project = await get_project_for_user_or_404(slug, current_user, session)
    content = await read_upload_with_limit(file, ALLOWED_CSV_TYPES)

    try:
        try:
            string_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "File must be UTF-8 encoded") from None
        reader = csv.DictReader(io.StringIO(string_content))

        created = 0
        skipped = 0
        invalid = 0
        count = 0
        for row in reader:
            count += 1
            if count > 1000:
                break

            method = row.get("method", "").upper()
            path = row.get("path", "")

            # A row is invalid if method is not in the allowed set OR path is empty
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"} or not path:
                invalid += 1
                continue

            desc = row.get("description", "")

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
                        project_id=project.id,
                        method=method,
                        path=path,
                        description=desc,
                    )
                )
                created += 1

        await session.commit()
        logger.info(
            "import.csv project=%s created=%d skipped=%d invalid=%d",
            slug,
            created,
            skipped,
            invalid,
        )
        return {
            "created": created,
            "skipped": skipped,
            "invalid": invalid,
            "processed": count,
            "truncated": count >= 1000,
        }
    except HTTPException:
        raise
    except Exception:
        await session.rollback()
        logger.exception("CSV import failed for project %s", slug)
        raise HTTPException(
            status_code=500,
            detail="Import failed. Check your CSV structure and try again.",
        ) from None


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

        if len(data) > 200:
            raise HTTPException(400, "Too many roles in YAML (max 200)")

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
        new_edges: list[tuple[str, str]] = []
        perm_count = 0

        for role_name, modules in data.items():
            if not isinstance(role_name, str) or not isinstance(modules, dict):
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
                                new_edges.append((parent_id, role_id))
                    continue

                if not isinstance(actions, dict):
                    continue

                for action_name, description in actions.items():
                    if not action_name:
                        continue
                    perm_name = f"{module_name}.{action_name}"
                    perm_count += 1
                    if perm_count > 500:
                        raise HTTPException(
                            400, "Too many permissions in YAML (max 500)"
                        )

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

        if len(new_edges) > 1000:
            await session.rollback()
            raise HTTPException(400, "Too many inheritance edges (max 1000)")

        # Fetch existing edges for roles in this project to detect cross-batch cycles
        existing_result = await session.execute(
            select(RoleInheritance).where(
                RoleInheritance.parent_role_id.in_(list(role_map.values()))
            )
        )
        existing_edges = [
            (row.parent_role_id, row.child_role_id)
            for row in existing_result.scalars().all()
        ]
        all_edges = existing_edges + new_edges
        if _has_cycle(all_edges):
            await session.rollback()
            raise HTTPException(400, "Cycle detected in role inheritance")

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
