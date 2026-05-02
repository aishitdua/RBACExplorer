# Code Quality Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix six confirmed bugs and code quality issues found in the backend code review: non-string YAML key crash, UTF-8 decode error surfacing as 500, duplicate function names in FastAPI export, misleading permission-count error message, unbounded CTE traversal in analyze endpoint, and local imports scattered inside function bodies.

**Architecture:** All fixes are isolated to existing files — no new files, no schema changes. Each fix is a surgical edit with a corresponding test added to the existing test file for that router. Tests use the established conftest pattern (SQLite in-memory, `client` fixture, auth override).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async), pytest-asyncio, httpx AsyncClient, SQLite (tests) / PostgreSQL (prod).

---

## Files Modified

| File                              | What changes                                                       |
| --------------------------------- | ------------------------------------------------------------------ |
| `backend/app/routers/import_.py`  | Three fixes: non-string key guard, UTF-8 catch, perm_count message |
| `backend/app/routers/export.py`   | Duplicate func_name dedup + move 3 local imports to module level   |
| `backend/app/routers/analyze.py`  | Scope ancestors CTE base case to project + move 2 local imports    |
| `backend/app/routers/roles.py`    | Move 1 local import (`selectinload`) to module level               |
| `backend/app/routers/projects.py` | Move 2 local imports (`delete`, model imports) to module level     |
| `backend/tests/test_import.py`    | Add 3 tests (non-string key, UTF-8, perm_count)                    |
| `backend/tests/test_export.py`    | Add 1 test (duplicate func_name dedup)                             |
| `backend/tests/test_analyze.py`   | Add 1 test (ancestors CTE correctness after scope fix)             |

---

## Task 1: Fix non-string YAML key crash (import\_.py)

**Context:** YAML allows non-string keys (integers like `42:`, booleans like `true:`). The first pass `ensure_role()` correctly rejects them and returns `None` without adding to `role_map`. But the second-pass guard `if not role_name or not isinstance(modules, dict)` does NOT catch integer keys — `not 42` is `False` in Python. The second pass then hits `role_map[42]` → `KeyError` → swallowed as generic 500. The fix adds `isinstance(role_name, str)` to the second-pass guard so non-string keys are silently skipped, matching how `ensure_role` handles them.

**Files:**

- Modify: `backend/app/routers/import_.py` (second-pass loop guard, ~line 350)
- Modify: `backend/tests/test_import.py` (new test)

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_import.py`:

```python
async def test_yaml_import_integer_role_keys_returns_not_500(client):
    """Non-string YAML keys (e.g. integer `42:`) must not crash with 500."""
    await client.post("/api/v1/projects", json={"name": "Test"})
    # YAML with an integer key — yaml.safe_load parses `42` as int, not str
    yaml_bytes = b"42:\n  users:\n    list: view users\n"
    r = await client.post(
        "/api/v1/projects/test/import/yaml",
        files={"file": ("roles.yaml", yaml_bytes, "text/yaml")},
    )
    # Must not be 500 — integer keys should be silently skipped
    assert r.status_code != 500
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && pytest tests/test_import.py::test_yaml_import_integer_role_keys_returns_not_500 -v
```

Expected: FAIL — the current code returns 500.

- [ ] **Step 3: Fix the second-pass guard in import\_.py**

Find this line (~line 350 in `backend/app/routers/import_.py`):

```python
        for role_name, modules in data.items():
            if not role_name or not isinstance(modules, dict):
                continue
```

Change it to:

```python
        for role_name, modules in data.items():
            if not isinstance(role_name, str) or not isinstance(modules, dict):
                continue
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd backend && pytest tests/test_import.py::test_yaml_import_integer_role_keys_returns_not_500 -v
```

Expected: PASS.

- [ ] **Step 5: Run full import test suite to check for regressions**

```bash
cd backend && pytest tests/test_import.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/import_.py backend/tests/test_import.py
git commit -m "fix: skip non-string YAML role keys instead of crashing with KeyError"
```

---

## Task 2: Fix UTF-8 decode error returning 500 (import\_.py)

**Context:** `import_csv` calls `content.decode("utf-8")`. If a client uploads a file with a non-UTF-8 encoding (e.g., Latin-1 with accented characters), Python raises `UnicodeDecodeError`. This is a **client error** (wrong encoding), but the generic `except Exception` block catches it and returns HTTP 500. The fix catches `UnicodeDecodeError` specifically and returns 400 with a clear message before the generic handler runs.

**Files:**

- Modify: `backend/app/routers/import_.py` (inside `import_csv` try block, ~line 153)
- Modify: `backend/tests/test_import.py` (new test)

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_import.py`:

```python
async def test_csv_import_non_utf8_returns_400(client):
    """Non-UTF-8 CSV must return 400, not 500."""
    await client.post("/api/v1/projects", json={"name": "Test"})
    # Latin-1 encoded bytes — 0xe9 is 'é' in Latin-1, invalid in UTF-8
    latin1_csv = b"method,path,description\nGET,/caf\xe9,a caf\xe9\n"
    r = await client.post(
        "/api/v1/projects/test/import/csv",
        files={"file": ("data.csv", latin1_csv, "text/csv")},
    )
    assert r.status_code == 400
    assert "UTF-8" in r.json()["detail"]
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && pytest tests/test_import.py::test_csv_import_non_utf8_returns_400 -v
```

Expected: FAIL — current code returns 500.

- [ ] **Step 3: Add UnicodeDecodeError catch in import_csv**

In `backend/app/routers/import_.py`, inside the `import_csv` function, find:

```python
    try:
        string_content = content.decode("utf-8")
```

Replace with:

```python
    try:
        try:
            string_content = content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "File must be UTF-8 encoded")
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd backend && pytest tests/test_import.py::test_csv_import_non_utf8_returns_400 -v
```

Expected: PASS.

- [ ] **Step 5: Run full import test suite**

```bash
cd backend && pytest tests/test_import.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/import_.py backend/tests/test_import.py
git commit -m "fix: return 400 instead of 500 for non-UTF-8 CSV uploads"
```

---

## Task 3: Fix misleading perm*count error message (import*.py)

**Context:** `perm_count` increments once per (role × permission action) combination. If "users.list" is assigned to 10 roles, `perm_count` hits 10 — not 1. The error message "Too many permissions in YAML (max 500)" implies a limit on unique permissions, but it's actually a limit on role-permission assignments. The fix changes only the error message string — no logic changes.

**Files:**

- Modify: `backend/app/routers/import_.py` (~line 387)
- Modify: `backend/tests/test_import.py` (new test verifying error message text)

- [ ] **Step 1: Write the test**

Add to `backend/tests/test_import.py`:

```python
async def test_yaml_import_perm_assignment_limit_message(client):
    """Over-limit YAML must mention 'assignments' in error, not just 'permissions'."""
    await client.post("/api/v1/projects", json={"name": "Test"})
    # Build YAML with 501 (role, action) combinations: 1 role × 501 actions
    actions = "\n".join(f"  act{i}: desc" for i in range(502))
    yaml_bytes = f"admin:\n  mod:\n{actions}\n".encode()
    r = await client.post(
        "/api/v1/projects/test/import/yaml",
        files={"file": ("roles.yaml", yaml_bytes, "text/yaml")},
    )
    assert r.status_code == 400
    assert "assignment" in r.json()["detail"].lower()
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && pytest tests/test_import.py::test_yaml_import_perm_assignment_limit_message -v
```

Expected: FAIL — current message doesn't contain "assignment".

- [ ] **Step 3: Update the error message in import\_.py**

Find (~line 387 in `backend/app/routers/import_.py`):

```python
                    if perm_count > 500:
                        raise HTTPException(
                            400, "Too many permissions in YAML (max 500)"
                        )
```

Replace with:

```python
                    if perm_count > 500:
                        raise HTTPException(
                            400, "Too many permission assignments in YAML (max 500)"
                        )
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd backend && pytest tests/test_import.py::test_yaml_import_perm_assignment_limit_message -v
```

Expected: PASS.

- [ ] **Step 5: Run full import test suite**

```bash
cd backend && pytest tests/test_import.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/import_.py backend/tests/test_import.py
git commit -m "fix: clarify YAML perm limit error — counts assignments not unique permissions"
```

---

## Task 4: Fix duplicate function names in FastAPI export (export.py)

**Context:** Two resources with paths that sanitize to the same identifier produce duplicate `async def` function names in the generated Python file (e.g., `/api/users` and `/api_users` both become `get_api_users`). Python silently uses the last definition — the first route disappears with no warning. The fix tracks seen function names and appends an incrementing suffix (`_2`, `_3`, ...) on collision.

**Files:**

- Modify: `backend/app/routers/export.py` (inside `export_fastapi`, ~line 51)
- Modify: `backend/tests/test_export.py` (new test)

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_export.py`:

```python
async def test_export_fastapi_deduplicates_func_names(client):
    """Paths that sanitize to the same identifier must get unique function names."""
    await client.post("/api/v1/projects", json={"name": "Test"})
    perm1 = (await client.post("/api/v1/projects/test/permissions", json={"name": "p1"})).json()
    perm2 = (await client.post("/api/v1/projects/test/permissions", json={"name": "p2"})).json()
    # /api/users and /api_users both sanitize to 'api_users'
    res1 = (await client.post("/api/v1/projects/test/resources", json={"method": "GET", "path": "/api/users"})).json()
    res2 = (await client.post("/api/v1/projects/test/resources", json={"method": "GET", "path": "/api_users"})).json()
    await client.post(f"/api/v1/projects/test/permissions/{perm1['id']}/resources/{res1['id']}")
    await client.post(f"/api/v1/projects/test/permissions/{perm2['id']}/resources/{res2['id']}")

    r = await client.get("/api/v1/projects/test/export/fastapi")
    assert r.status_code == 200
    code = r.text

    # Both function definitions must be present with distinct names
    assert "async def get_api_users(" in code
    assert "async def get_api_users_2(" in code

    # Generated code must be valid Python
    import ast
    ast.parse(code)
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd backend && pytest tests/test_export.py::test_export_fastapi_deduplicates_func_names -v
```

Expected: FAIL — current code emits duplicate `get_api_users` and the second assertion fails.

- [ ] **Step 3: Add deduplication logic in export_fastapi**

In `backend/app/routers/export.py`, inside the `export_fastapi` function, find the block that starts with `lines = [...]`. Just before the `for row in rows:` loop, add the tracking dict. Then wrap the func_name assignment:

Find:

```python
    for row in rows:
        method = row.method.lower()
        # Sanitize path for function name
        safe_path = (
            row.path.strip("/")
            .replace("/", "_")
            .replace("{", "")
            .replace("}", "")
            .replace("-", "_")
        )
        func_name = f"{method}_{safe_path}" if safe_path else method
```

Replace with:

```python
    seen_func_names: dict[str, int] = {}

    for row in rows:
        method = row.method.lower()
        # Sanitize path for function name
        safe_path = (
            row.path.strip("/")
            .replace("/", "_")
            .replace("{", "")
            .replace("}", "")
            .replace("-", "_")
        )
        base_name = f"{method}_{safe_path}" if safe_path else method
        if base_name in seen_func_names:
            seen_func_names[base_name] += 1
            func_name = f"{base_name}_{seen_func_names[base_name]}"
        else:
            seen_func_names[base_name] = 1
            func_name = base_name
```

- [ ] **Step 4: Run test to confirm it passes**

```bash
cd backend && pytest tests/test_export.py::test_export_fastapi_deduplicates_func_names -v
```

Expected: PASS.

- [ ] **Step 5: Run full export test suite**

```bash
cd backend && pytest tests/test_export.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/export.py backend/tests/test_export.py
git commit -m "fix: deduplicate generated function names in FastAPI export"
```

---

## Task 5: Scope ancestors CTE to current project (analyze.py)

**Context:** The `ancestors` CTE in `analyze_project` (used to detect redundant permission assignments) starts with `SELECT parent_role_id, child_role_id FROM role_inheritance` — this is **all rows** across all projects. The final `WHERE r.project_id = :pid` filters the output correctly, but the DB must compute the full transitive closure for every project first. The fix adds a project-scoped JOIN on the base case so the CTE only traverses edges relevant to the current project.

**Files:**

- Modify: `backend/app/routers/analyze.py` (the `ancestors` CTE base case, ~line 62)
- Modify: `backend/tests/test_analyze.py` (new test verifying correctness after change)

- [ ] **Step 1: Write the test**

Add to `backend/tests/test_analyze.py`:

```python
async def test_analyze_redundant_assignment_scoped_to_project(client):
    """
    Redundant assignment detection must work correctly per project and must not
    return findings from other projects.
    """
    # Project A: child inherits from parent, both have 'read' permission → redundant
    await client.post("/api/v1/projects", json={"name": "A"})
    parent_a = (await client.post("/api/v1/projects/a/roles", json={"name": "parent"})).json()
    child_a = (await client.post("/api/v1/projects/a/roles", json={"name": "child"})).json()
    perm_a = (await client.post("/api/v1/projects/a/permissions", json={"name": "read"})).json()
    await client.post(f"/api/v1/projects/a/roles/{child_a['id']}/permissions/{perm_a['id']}")
    await client.post(f"/api/v1/projects/a/roles/{parent_a['id']}/permissions/{perm_a['id']}")
    await client.post(f"/api/v1/projects/a/roles/{child_a['id']}", json={"parent_role_id": parent_a["id"]})

    # Project B: completely separate, no redundancy
    await client.post("/api/v1/projects", json={"name": "B"})

    r = await client.get("/api/v1/projects/a/analyze")
    assert r.status_code == 200
    findings = r.json()["findings"]
    redundant = [f for f in findings if f["type"] == "redundant_assignment"]
    assert len(redundant) == 1
    assert redundant[0]["detail"]["role_name"] == "child"

    # Project B should have zero findings
    r2 = await client.get("/api/v1/projects/b/analyze")
    assert r2.status_code == 200
    assert r2.json()["findings"] == []
```

- [ ] **Step 2: Run test to confirm it passes already (baseline)**

```bash
cd backend && pytest tests/test_analyze.py::test_analyze_redundant_assignment_scoped_to_project -v
```

Expected: PASS (the logic was already correct, we're just confirming before the refactor).

- [ ] **Step 3: Update the ancestors CTE base case in analyze.py**

In `backend/app/routers/analyze.py`, find the `ancestors` CTE (inside `analyze_project`, ~line 62):

```python
        text(f"""
        WITH RECURSIVE ancestors AS (
            SELECT parent_role_id, child_role_id, 0 AS depth FROM role_inheritance
            UNION ALL
            SELECT ri.parent_role_id, a.child_role_id, a.depth + 1
            FROM role_inheritance ri
            JOIN ancestors a ON ri.child_role_id = a.parent_role_id
            WHERE a.depth < {MAX_INHERITANCE_DEPTH}
        )
```

Replace with:

```python
        text(f"""
        WITH RECURSIVE ancestors AS (
            SELECT ri.parent_role_id, ri.child_role_id, 0 AS depth
            FROM role_inheritance ri
            JOIN roles r ON r.id = ri.child_role_id AND r.project_id = :pid
            UNION ALL
            SELECT ri.parent_role_id, a.child_role_id, a.depth + 1
            FROM role_inheritance ri
            JOIN ancestors a ON ri.child_role_id = a.parent_role_id
            WHERE a.depth < {MAX_INHERITANCE_DEPTH}
        )
```

- [ ] **Step 4: Run the test again to confirm it still passes after refactor**

```bash
cd backend && pytest tests/test_analyze.py::test_analyze_redundant_assignment_scoped_to_project -v
```

Expected: PASS.

- [ ] **Step 5: Run full analyze test suite**

```bash
cd backend && pytest tests/test_analyze.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/analyze.py backend/tests/test_analyze.py
git commit -m "perf: scope ancestors CTE base case to current project in analyze endpoint"
```

---

## Task 6: Move local imports to module level (multiple files)

**Context:** Several files have imports inside function bodies. These were likely left during refactoring. Python re-evaluates them on every function call (minor performance hit) and they obscure the file's actual dependencies. No logic changes — imports move up, everything else stays identical.

**Files:**

- Modify: `backend/app/routers/export.py`
- Modify: `backend/app/routers/analyze.py`
- Modify: `backend/app/routers/roles.py`
- Modify: `backend/app/routers/projects.py`

No new tests needed — all existing tests cover these paths.

- [ ] **Step 1: Fix export.py — move imports out of export_yaml**

In `backend/app/routers/export.py`, find the top of the file. The current top-level imports are:

```python
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, text

from app.dependencies import CurrentUser, DBSession, get_project_for_user_or_404
```

Replace with:

```python
import yaml
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DBSession, get_project_for_user_or_404
from app.models import Role, RoleInheritance, RolePermission
```

Then inside `export_yaml`, remove the three local import lines:

```python
    import yaml                                       # DELETE THIS LINE
    from sqlalchemy.orm import selectinload           # DELETE THIS LINE
    from app.models import Role, RoleInheritance, RolePermission  # DELETE THIS LINE
```

- [ ] **Step 2: Fix analyze.py — move imports out of diff_role**

In `backend/app/routers/analyze.py`, find the top-level imports. Currently they end with:

```python
from app.models import Permission, Resource
```

Replace with:

```python
from app.models import Permission, PermissionResource, Resource
from sqlalchemy import select as sa_select
```

Note: `select` is already imported as `select` from sqlalchemy at the top. Add `sa_select` as an alias alongside it:

Actually, the file already has `from sqlalchemy import select, text`. Change that to:

```python
from sqlalchemy import select, text
from sqlalchemy import select as sa_select  # alias used in diff_role closure
```

Wait — that creates two imports of the same thing. Better approach: the local import uses `sa_select` only to avoid shadowing the outer `select`. Since `select` isn't shadowed in the closure anyway, just use `select` directly. Find in `diff_role`:

```python
        from sqlalchemy import select as sa_select   # DELETE THIS LINE
        from app.models import PermissionResource    # DELETE THIS LINE

        res_result = await session.execute(
            sa_select(PermissionResource.resource_id).where(
```

Delete those two local import lines and change `sa_select` → `select` in the same block:

```python
        res_result = await session.execute(
            select(PermissionResource.resource_id).where(
```

Then add `PermissionResource` to the top-level models import in `analyze.py`:

```python
from app.models import Permission, PermissionResource, Resource
```

- [ ] **Step 3: Fix roles.py — move selectinload out of list_roles**

In `backend/app/routers/roles.py`, find the top-level imports. Add `selectinload`:

```python
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
```

Then inside `list_roles`, delete:

```python
    from sqlalchemy.orm import selectinload   # DELETE THIS LINE
```

- [ ] **Step 4: Fix projects.py — move delete and model imports out of clean_project**

In `backend/app/routers/projects.py`, current top-level imports end with:

```python
from sqlalchemy import select
```

Change to:

```python
from sqlalchemy import delete, select
from app.models import Permission, Project, Resource, Role
```

Then inside `clean_project`, delete the local import lines:

```python
    from sqlalchemy import delete                          # DELETE THIS LINE
    from app.models import Permission, Resource, Role      # DELETE THIS LINE (check exact text)
```

- [ ] **Step 5: Run full test suite to verify nothing broke**

```bash
cd backend && pytest -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/export.py backend/app/routers/analyze.py \
        backend/app/routers/roles.py backend/app/routers/projects.py
git commit -m "refactor: move function-body imports to module level"
```

---

## Task 7: Final verification

- [ ] **Step 1: Run the complete test suite one final time**

```bash
cd backend && pytest -v --tb=short
```

Expected: all tests pass, no warnings about import errors.

- [ ] **Step 2: Verify the changed files have no leftover local imports**

```bash
grep -n "^\s\+import\|^\s\+from .* import" \
  backend/app/routers/export.py \
  backend/app/routers/analyze.py \
  backend/app/routers/roles.py \
  backend/app/routers/projects.py
```

Expected: no output (no indented imports remaining).

---

## Summary of Changes

| Task | Files                                        | Type               |
| ---- | -------------------------------------------- | ------------------ |
| 1    | import\_.py, test_import.py                  | Bug fix + test     |
| 2    | import\_.py, test_import.py                  | Bug fix + test     |
| 3    | import\_.py, test_import.py                  | Message fix + test |
| 4    | export.py, test_export.py                    | Bug fix + test     |
| 5    | analyze.py, test_analyze.py                  | Perf fix + test    |
| 6    | export.py, analyze.py, roles.py, projects.py | Refactor           |
| 7    | —                                            | Verification       |
