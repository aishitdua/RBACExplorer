# RBACExplorer — Design Spec

**Date:** 2026-04-24  
**Status:** Approved

---

## Overview

RBACExplorer is a developer tool for designing, visualising, and simulating Role-Based Access Control (RBAC) for web applications. Developers define their app's roles, permissions, and API endpoints in one place, then explore the full access surface of each role through an interactive graph and simulator. The tool also detects anomalies in the RBAC config and exports working FastAPI dependency code.

**Target user:** A developer building their own SaaS or web app who wants to model and verify their access control design before or during implementation.

**What makes it unique:**
- Hierarchical roles with multi-level inheritance visualised as a force-directed graph
- Endpoint-level permission mapping (permissions map to HTTP method + path pairs)
- Permission simulator — pick a role, see every endpoint it can and cannot access, including inherited access
- Conflict/anomaly detection engine
- FastAPI `Depends()` code export directly from the UI
- OpenAPI spec import to auto-populate the endpoint registry

---

## Stack

| Layer | Technology | Platform |
|---|---|---|
| Frontend | React + Cytoscape.js | Vercel (free forever) |
| Backend | Python + FastAPI | Render (free tier, cold starts ok) |
| Database | PostgreSQL (SQLAlchemy async) | Neon (free forever) |

**No authentication.** Access is project-scoped via a unique slug URL. Anyone with the slug can view and edit the project. This is intentional for a portfolio demo — auth can be layered on later.

---

## Data Model

### `projects`
```
id          UUID primary key
slug        TEXT unique          -- shareable URL identifier e.g. "my-saas-app"
name        TEXT
description TEXT
created_at  TIMESTAMP
```

### `roles`
```
id          UUID primary key
project_id  UUID foreign key → projects
name        TEXT
description TEXT
color       TEXT                 -- hex color for graph node
created_at  TIMESTAMP
```

### `role_inheritance`
```
parent_role_id  UUID foreign key → roles
child_role_id   UUID foreign key → roles
PRIMARY KEY (parent_role_id, child_role_id)
```
A child role inherits all permissions of its parent(s). A role may have multiple parents (DAG, not strict tree).

### `permissions`
```
id          UUID primary key
project_id  UUID foreign key → projects
name        TEXT                 -- e.g. "read_users"
description TEXT
```

### `role_permissions`
```
role_id         UUID foreign key → roles
permission_id   UUID foreign key → permissions
PRIMARY KEY (role_id, permission_id)
```

### `resources`
```
id          UUID primary key
project_id  UUID foreign key → projects
method      TEXT                 -- GET, POST, PUT, DELETE, PATCH
path        TEXT                 -- e.g. /users/{id}
description TEXT
```

### `permission_resources`
```
permission_id   UUID foreign key → permissions
resource_id     UUID foreign key → resources
PRIMARY KEY (permission_id, resource_id)
```

---

## API Design

All endpoints are prefixed `/api/v1`. All responses are JSON.

### Projects
```
POST   /projects                  -- create project; body: { name, description, slug? }
                                  -- slug is user-provided or auto-generated from name
                                  -- returns full project object including slug
GET    /projects/{slug}           -- get project + summary stats
DELETE /projects/{slug}           -- delete project and all data
```

### Roles
```
GET    /projects/{slug}/roles            -- list roles
POST   /projects/{slug}/roles            -- create role
PATCH  /projects/{slug}/roles/{id}       -- update role
DELETE /projects/{slug}/roles/{id}       -- delete role
POST   /projects/{slug}/roles/{id}/parents        -- add parent role
DELETE /projects/{slug}/roles/{id}/parents/{pid}  -- remove parent role
```

### Permissions
```
GET    /projects/{slug}/permissions           -- list permissions
POST   /projects/{slug}/permissions           -- create permission
PATCH  /projects/{slug}/permissions/{id}      -- update permission
DELETE /projects/{slug}/permissions/{id}      -- delete permission
POST   /projects/{slug}/roles/{id}/permissions/{pid}      -- assign to role
DELETE /projects/{slug}/roles/{id}/permissions/{pid}      -- unassign from role
```

### Resources (Endpoints)
```
GET    /projects/{slug}/resources             -- list resources
POST   /projects/{slug}/resources             -- create resource
PATCH  /projects/{slug}/resources/{id}        -- update resource
DELETE /projects/{slug}/resources/{id}        -- delete resource
POST   /projects/{slug}/permissions/{id}/resources/{rid}      -- map to permission
DELETE /projects/{slug}/permissions/{id}/resources/{rid}      -- unmap from permission
```

### Intelligence
```
GET    /projects/{slug}/simulate/{role_id}    -- resolve full access for a role
GET    /projects/{slug}/analyze               -- return all conflicts/anomalies
GET    /projects/{slug}/diff/{role_id}        -- show permission impact of pending role edit (query params: add_permissions[], remove_permissions[], add_parents[], remove_parents[])
```

### Export / Import
```
GET    /projects/{slug}/export/fastapi        -- return FastAPI Depends() code stubs
POST   /projects/{slug}/import/openapi        -- body: OpenAPI JSON, creates resources
```

---

## Frontend Structure

### Tabs (per project workspace)

**Graph tab**
- Force-directed graph rendered with Cytoscape.js
- Node types: roles (circles, sized by total resolved permission count) and optionally permissions (smaller circles, togglable)
- Edges: solid for inheritance, dashed for permission assignment
- Click a role node → highlights its subtree and opens a details drawer
- Drawer shows: direct permissions, inherited permissions (with source role), resolved endpoints

**Roles tab**
- Table of all roles with name, color, parent count, permission count
- Inline create/edit/delete
- Parent assignment via multi-select dropdown

**Permissions tab**
- Table of all permissions with name, assigned roles, mapped endpoints
- Inline create/edit/delete
- Endpoint mapping via multi-select

**Resources tab**
- Table of all resources (method + path)
- Inline create/edit/delete
- Bulk import via OpenAPI JSON paste modal

**Simulator tab**
- Role selector dropdown
- Full list of all resources in the project
- Each resource shows: ALLOWED (green) or DENIED (red)
- Inherited permissions shown with source role label
- Conflict/anomaly panel at the bottom of this tab

---

## Permission Simulator Logic

Given role X:
1. Walk `role_inheritance` upward recursively to collect all ancestor role IDs (including X itself)
2. Collect all `permission_id`s from `role_permissions` for those role IDs
3. Collect all `resource_id`s from `permission_resources` for those permission IDs
4. Return: allowed resources (with which permission + which role granted it), and denied resources (all project resources minus allowed)

This is a pure read query — no mutation. Implemented as a recursive CTE in Postgres for efficiency.

---

## Conflict / Anomaly Detection

Run on demand via `GET /projects/{slug}/analyze`. Returns a list of findings:

| Type | Description |
|---|---|
| `orphaned_permission` | Permission exists but is assigned to no role |
| `empty_role` | Role has no direct permissions and no children |
| `redundant_assignment` | Role explicitly assigned a permission it already inherits from a parent |
| `permission_shadowing` | Child role redefines a permission the parent already grants (identical resource mapping) |
| `circular_inheritance` | Role inheritance graph contains a cycle (blocked at write time, but flagged if detected) |

Circular inheritance is also validated at write time — the `POST /roles/{id}/parents` endpoint rejects assignments that would create a cycle.

---

## FastAPI Code Export

`GET /projects/{slug}/export/fastapi` returns a Python file as plain text containing:

```python
# Generated by RBACExplorer
from fastapi import Depends, HTTPException

def require_permission(permission: str):
    def dependency(current_permission: str = Depends(get_current_permission)):
        if current_permission != permission:
            raise HTTPException(status_code=403, detail="Forbidden")
    return dependency

# Route stubs
@router.get("/users")
async def list_users(_=Depends(require_permission("read_users"))):
    ...

@router.post("/users")
async def create_user(_=Depends(require_permission("create_user"))):
    ...
```

One stub per resource, using the permission mapped to that resource.

---

## OpenAPI Import

`POST /projects/{slug}/import/openapi` accepts an OpenAPI 3.x JSON body. The backend:
1. Parses `paths` object
2. For each path + method combination, creates a `resource` record (if not already existing by method+path)
3. Returns count of created vs skipped resources

Does not create permissions or assign mappings automatically — the developer does that after import.

---

## Deployment

```
Frontend  →  Vercel        (auto-deploy from GitHub, free forever)
Backend   →  Render        (web service, free tier, cold starts after inactivity)
Database  →  Neon          (serverless Postgres, free forever, always accessible)
```

Backend exposes a `GET /health` endpoint. Frontend README notes the cold start behaviour.

`.superpowers/` added to `.gitignore`.

---

## Out of Scope

- User authentication / accounts
- Real-time collaboration
- Integration with external IAM providers (Auth0, AWS IAM, Okta)
- Attribute-based access control (ABAC)
- Audit logging
- Role versioning / history
