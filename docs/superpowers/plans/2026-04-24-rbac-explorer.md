# RBACExplorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack RBAC visualizer with hierarchical roles, permission simulation, conflict detection, and FastAPI code export.

**Architecture:** Monorepo with `backend/` (FastAPI + async SQLAlchemy + Neon Postgres) and `frontend/` (React + Cytoscape.js + Vite). Backend on Render, frontend on Vercel, DB on Neon. All APIs prefixed `/api/v1`, project-scoped by slug.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic, pytest, httpx, aiosqlite / React 18, Vite, Cytoscape.js + cytoscape-fcose, Axios, React Router v6, Tailwind CSS, Vitest, @testing-library/react

---

## File Map

```
RBACExplorer/
  backend/
    app/
      main.py           -- FastAPI app, CORS, router registration, /health
      database.py       -- Neon async engine, session factory, get_session dep
      models.py         -- SQLAlchemy ORM: all 7 tables
      schemas.py        -- Pydantic v2 request/response models
      routers/
        projects.py     -- POST/GET/DELETE /projects
        roles.py        -- CRUD + inheritance + cycle detection
        permissions.py  -- CRUD + role assignment + resource mapping
        resources.py    -- CRUD + permission mapping
        simulate.py     -- recursive CTE access resolver
        analyze.py      -- conflict/anomaly detection
        export.py       -- FastAPI Depends() code generator
        import_.py      -- OpenAPI JSON parser → resources
    tests/
      conftest.py       -- async test client + SQLite test DB fixture
      test_projects.py
      test_roles.py
      test_permissions.py
      test_resources.py
      test_simulate.py
      test_analyze.py
      test_export.py
      test_import.py
    requirements.txt
    requirements-dev.txt
    .env.example
    render.yaml
  frontend/
    src/
      main.jsx          -- ReactDOM.render, BrowserRouter
      App.jsx           -- Routes: / and /:slug
      api/
        client.js       -- axios instance with base URL from env
        projects.js     -- createProject, getProject
        roles.js        -- listRoles, createRole, updateRole, deleteRole, addParent, removeParent
        permissions.js  -- listPermissions, createPermission, updatePermission, deletePermission, assignToRole, unassignFromRole, mapToResource, unmapFromResource
        resources.js    -- listResources, createResource, updateResource, deleteResource
        simulate.js     -- simulateRole
        analyze.js      -- analyzeProject
        export_.js      -- exportFastapi
        import_.js      -- importOpenapi
      pages/
        HomePage.jsx    -- create project form + open by slug
        WorkspacePage.jsx -- fetches project, renders tab shell
      tabs/
        GraphTab.jsx    -- Cytoscape.js force-directed graph
        RolesTab.jsx    -- role CRUD table
        PermissionsTab.jsx
        ResourcesTab.jsx -- + OpenAPI import modal
        SimulatorTab.jsx -- + conflict panel + code export modal
      components/
        ConflictPanel.jsx
        CodeExportModal.jsx
        OpenAPIImportModal.jsx
    package.json
    vite.config.js
    vercel.json
    index.html
```

---

## Task 1: Backend scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/.env.example`
- Create: `backend/app/main.py`
- Create: `backend/app/database.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
alembic==1.13.1
pydantic==2.7.1
pydantic-settings==2.2.1
python-slugify==8.0.4
python-dotenv==1.0.1
```

- [ ] **Step 2: Create requirements-dev.txt**

```
pytest==8.2.0
pytest-asyncio==0.23.7
httpx==0.27.0
aiosqlite==0.20.0
```

- [ ] **Step 3: Create .env.example**

```
DATABASE_URL=postgresql+asyncpg://user:password@host/dbname
```

- [ ] **Step 4: Create backend/app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str

    class Config:
        env_file = ".env"


settings = Settings()


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session
```

- [ ] **Step 5: Create backend/app/main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import projects, roles, permissions, resources, simulate, analyze, export, import_

app = FastAPI(title="RBACExplorer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
app.include_router(simulate.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(import_.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Create routers package**

```bash
mkdir -p backend/app/routers && touch backend/app/routers/__init__.py && touch backend/app/__init__.py
```

- [ ] **Step 7: Install dependencies and verify server starts**

```bash
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
DATABASE_URL=sqlite+aiosqlite:///./dev.db uvicorn app.main:app --reload
```

Expected: Uvicorn running on http://127.0.0.1:8000

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold FastAPI backend with CORS and health endpoint"
```

---

## Task 2: Database models

**Files:**
- Create: `backend/app/models.py`

- [ ] **Step 1: Write models.py**

```python
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.database import Base


def new_uuid():
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    roles: Mapped[list["Role"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    permissions: Mapped[list["Permission"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    resources: Mapped[list["Resource"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    color: Mapped[str] = mapped_column(String, default="#60a5fa")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    project: Mapped["Project"] = relationship(back_populates="roles")
    __table_args__ = (UniqueConstraint("project_id", "name"),)


class RoleInheritance(Base):
    __tablename__ = "role_inheritance"

    parent_role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    child_role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")

    project: Mapped["Project"] = relationship(back_populates="permissions")
    __table_args__ = (UniqueConstraint("project_id", "name"),)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[str] = mapped_column(String, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class Resource(Base):
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id", ondelete="CASCADE"))
    method: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")

    project: Mapped["Project"] = relationship(back_populates="resources")
    __table_args__ = (UniqueConstraint("project_id", "method", "path"),)


class PermissionResource(Base):
    __tablename__ = "permission_resources"

    permission_id: Mapped[str] = mapped_column(String, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    resource_id: Mapped[str] = mapped_column(String, ForeignKey("resources.id", ondelete="CASCADE"), primary_key=True)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add SQLAlchemy ORM models for all 7 tables"
```

---

## Task 3: Pydantic schemas + test infrastructure

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write schemas.py**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    slug: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "#60a5fa"


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class RoleOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    color: str

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    name: str
    description: str = ""


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PermissionOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: str

    model_config = {"from_attributes": True}


class ResourceCreate(BaseModel):
    method: str
    path: str
    description: str = ""


class ResourceUpdate(BaseModel):
    method: Optional[str] = None
    path: Optional[str] = None
    description: Optional[str] = None


class ResourceOut(BaseModel):
    id: str
    project_id: str
    method: str
    path: str
    description: str

    model_config = {"from_attributes": True}


class SimulatedResource(BaseModel):
    resource_id: str
    method: str
    path: str
    allowed: bool
    granted_by_permission: Optional[str] = None
    granted_by_role: Optional[str] = None


class SimulateOut(BaseModel):
    role_id: str
    role_name: str
    resources: list[SimulatedResource]


class ConflictFinding(BaseModel):
    type: str
    detail: dict


class AnalyzeOut(BaseModel):
    findings: list[ConflictFinding]


class AddParentBody(BaseModel):
    parent_role_id: str


class AssignPermissionBody(BaseModel):
    pass


class MapResourceBody(BaseModel):
    pass
```

- [ ] **Step 2: Write tests/conftest.py**

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.database import Base, get_session

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_engine):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 3: Add pytest.ini**

```ini
# backend/pytest.ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas.py backend/tests/ backend/pytest.ini
git commit -m "feat: add Pydantic schemas and async test infrastructure"
```

---

## Task 4: Projects API

**Files:**
- Create: `backend/app/routers/projects.py`
- Create: `backend/tests/test_projects.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_projects.py
import pytest


async def test_create_project_auto_slug(client):
    r = await client.post("/api/v1/projects", json={"name": "My SaaS App"})
    assert r.status_code == 201
    data = r.json()
    assert data["slug"] == "my-saas-app"
    assert data["name"] == "My SaaS App"


async def test_create_project_custom_slug(client):
    r = await client.post("/api/v1/projects", json={"name": "App", "slug": "custom-slug"})
    assert r.status_code == 201
    assert r.json()["slug"] == "custom-slug"


async def test_get_project(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r = await client.get("/api/v1/projects/test")
    assert r.status_code == 200
    assert r.json()["name"] == "Test"


async def test_get_project_not_found(client):
    r = await client.get("/api/v1/projects/nonexistent")
    assert r.status_code == 404


async def test_delete_project(client):
    await client.post("/api/v1/projects", json={"name": "Delete Me"})
    r = await client.delete("/api/v1/projects/delete-me")
    assert r.status_code == 204
    r2 = await client.get("/api/v1/projects/delete-me")
    assert r2.status_code == 404
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd backend && source venv/bin/activate && pytest tests/test_projects.py -v
```

Expected: ImportError or 404/500 errors — routers not implemented yet.

- [ ] **Step 3: Write projects.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from slugify import slugify
from app.database import get_session
from app.models import Project
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, session: AsyncSession = Depends(get_session)):
    slug = body.slug or slugify(body.name)
    existing = await session.scalar(select(Project).where(Project.slug == slug))
    if existing:
        raise HTTPException(400, "Slug already taken")
    project = Project(slug=slug, name=body.name, description=body.description)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/projects/{slug}", response_model=ProjectOut)
async def get_project(slug: str, session: AsyncSession = Depends(get_session)):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.delete("/projects/{slug}", status_code=204)
async def delete_project(slug: str, session: AsyncSession = Depends(get_session)):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")
    await session.delete(project)
    await session.commit()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_projects.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/projects.py backend/tests/test_projects.py
git commit -m "feat: add projects CRUD API with slug generation"
```

---

## Task 5: Roles API with cycle detection

**Files:**
- Create: `backend/app/routers/roles.py`
- Create: `backend/tests/test_roles.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_roles.py
import pytest


@pytest.fixture
async def project(client):
    r = await client.post("/api/v1/projects", json={"name": "Test"})
    return r.json()


async def test_create_role(client, project):
    r = await client.post(f"/api/v1/projects/test/roles", json={"name": "admin", "color": "#ff0000"})
    assert r.status_code == 201
    assert r.json()["name"] == "admin"


async def test_list_roles(client, project):
    await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    await client.post("/api/v1/projects/test/roles", json={"name": "viewer"})
    r = await client.get("/api/v1/projects/test/roles")
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_add_parent(client, project):
    r1 = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r2 = await client.post("/api/v1/projects/test/roles", json={"name": "editor"})
    admin_id = r1.json()["id"]
    editor_id = r2.json()["id"]
    r = await client.post(f"/api/v1/projects/test/roles/{editor_id}/parents", json={"parent_role_id": admin_id})
    assert r.status_code == 200


async def test_cycle_detection(client, project):
    r1 = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r2 = await client.post("/api/v1/projects/test/roles", json={"name": "editor"})
    admin_id = r1.json()["id"]
    editor_id = r2.json()["id"]
    # editor inherits from admin
    await client.post(f"/api/v1/projects/test/roles/{editor_id}/parents", json={"parent_role_id": admin_id})
    # making admin inherit from editor would create a cycle
    r = await client.post(f"/api/v1/projects/test/roles/{admin_id}/parents", json={"parent_role_id": editor_id})
    assert r.status_code == 400


async def test_delete_role(client, project):
    r = await client.post("/api/v1/projects/test/roles", json={"name": "temp"})
    role_id = r.json()["id"]
    r = await client.delete(f"/api/v1/projects/test/roles/{role_id}")
    assert r.status_code == 204
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_roles.py -v
```

Expected: all fail (router not implemented)

- [ ] **Step 3: Write roles.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_session
from app.models import Project, Role, RoleInheritance
from app.schemas import RoleCreate, RoleUpdate, RoleOut, AddParentBody

router = APIRouter(tags=["roles"])


async def _get_project(slug: str, session: AsyncSession) -> Project:
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")
    return project


async def _get_role(role_id: str, project_id: str, session: AsyncSession) -> Role:
    role = await session.scalar(
        select(Role).where(Role.id == role_id, Role.project_id == project_id)
    )
    if not role:
        raise HTTPException(404, "Role not found")
    return role


async def _would_create_cycle(child_id: str, new_parent_id: str, session: AsyncSession) -> bool:
    """Returns True if making new_parent_id a parent of child_id would create a cycle."""
    result = await session.execute(
        text("""
        WITH RECURSIVE descendants AS (
            SELECT :child_id AS id
            UNION ALL
            SELECT ri.child_role_id
            FROM role_inheritance ri
            JOIN descendants d ON ri.parent_role_id = d.id
        )
        SELECT COUNT(*) FROM descendants WHERE id = :parent_id
        """),
        {"child_id": child_id, "parent_id": new_parent_id},
    )
    return result.scalar() > 0


@router.get("/projects/{slug}/roles", response_model=list[RoleOut])
async def list_roles(slug: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    result = await session.execute(select(Role).where(Role.project_id == project.id))
    return result.scalars().all()


@router.post("/projects/{slug}/roles", response_model=RoleOut, status_code=201)
async def create_role(slug: str, body: RoleCreate, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    role = Role(project_id=project.id, name=body.name, description=body.description, color=body.color)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


@router.patch("/projects/{slug}/roles/{role_id}", response_model=RoleOut)
async def update_role(slug: str, role_id: str, body: RoleUpdate, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    role = await _get_role(role_id, project.id, session)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(role, field, value)
    await session.commit()
    await session.refresh(role)
    return role


@router.delete("/projects/{slug}/roles/{role_id}", status_code=204)
async def delete_role(slug: str, role_id: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    role = await _get_role(role_id, project.id, session)
    await session.delete(role)
    await session.commit()


@router.post("/projects/{slug}/roles/{role_id}/parents")
async def add_parent(slug: str, role_id: str, body: AddParentBody, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    await _get_role(role_id, project.id, session)
    await _get_role(body.parent_role_id, project.id, session)
    if await _would_create_cycle(role_id, body.parent_role_id, session):
        raise HTTPException(400, "Adding this parent would create a cycle in the role hierarchy")
    existing = await session.scalar(
        select(RoleInheritance).where(
            RoleInheritance.child_role_id == role_id,
            RoleInheritance.parent_role_id == body.parent_role_id,
        )
    )
    if not existing:
        session.add(RoleInheritance(parent_role_id=body.parent_role_id, child_role_id=role_id))
        await session.commit()
    return {"ok": True}


@router.delete("/projects/{slug}/roles/{role_id}/parents/{parent_id}", status_code=204)
async def remove_parent(slug: str, role_id: str, parent_id: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    link = await session.scalar(
        select(RoleInheritance).where(
            RoleInheritance.child_role_id == role_id,
            RoleInheritance.parent_role_id == parent_id,
        )
    )
    if link:
        await session.delete(link)
        await session.commit()
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_roles.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/roles.py backend/tests/test_roles.py
git commit -m "feat: add roles API with hierarchical inheritance and cycle detection"
```

---

## Task 6: Permissions + Resources APIs

**Files:**
- Create: `backend/app/routers/permissions.py`
- Create: `backend/app/routers/resources.py`
- Create: `backend/tests/test_permissions.py`
- Create: `backend/tests/test_resources.py`

- [ ] **Step 1: Write failing tests for permissions**

```python
# backend/tests/test_permissions.py
import pytest


@pytest.fixture
async def setup(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_role = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post("/api/v1/projects/test/permissions", json={"name": "read_users"})
    return {"role_id": r_role.json()["id"], "perm_id": r_perm.json()["id"]}


async def test_create_permission(client, setup):
    r = await client.post("/api/v1/projects/test/permissions", json={"name": "delete_users"})
    assert r.status_code == 201
    assert r.json()["name"] == "delete_users"


async def test_list_permissions(client, setup):
    r = await client.get("/api/v1/projects/test/permissions")
    assert r.status_code == 200
    assert any(p["name"] == "read_users" for p in r.json())


async def test_assign_permission_to_role(client, setup):
    role_id = setup["role_id"]
    perm_id = setup["perm_id"]
    r = await client.post(f"/api/v1/projects/test/roles/{role_id}/permissions/{perm_id}")
    assert r.status_code == 200


async def test_unassign_permission_from_role(client, setup):
    role_id = setup["role_id"]
    perm_id = setup["perm_id"]
    await client.post(f"/api/v1/projects/test/roles/{role_id}/permissions/{perm_id}")
    r = await client.delete(f"/api/v1/projects/test/roles/{role_id}/permissions/{perm_id}")
    assert r.status_code == 204
```

- [ ] **Step 2: Write failing tests for resources**

```python
# backend/tests/test_resources.py
import pytest


@pytest.fixture
async def setup(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_perm = await client.post("/api/v1/projects/test/permissions", json={"name": "read_users"})
    r_res = await client.post("/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"})
    return {"perm_id": r_perm.json()["id"], "res_id": r_res.json()["id"]}


async def test_create_resource(client, setup):
    r = await client.post("/api/v1/projects/test/resources", json={"method": "POST", "path": "/users"})
    assert r.status_code == 201
    assert r.json()["method"] == "POST"


async def test_map_resource_to_permission(client, setup):
    perm_id = setup["perm_id"]
    res_id = setup["res_id"]
    r = await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    assert r.status_code == 200


async def test_unmap_resource_from_permission(client, setup):
    perm_id = setup["perm_id"]
    res_id = setup["res_id"]
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    r = await client.delete(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    assert r.status_code == 204
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
pytest tests/test_permissions.py tests/test_resources.py -v
```

Expected: all fail

- [ ] **Step 4: Write permissions.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Project, Permission, Role, RolePermission, PermissionResource, Resource
from app.schemas import PermissionCreate, PermissionUpdate, PermissionOut

router = APIRouter(tags=["permissions"])


async def _get_project(slug: str, session: AsyncSession) -> Project:
    p = await session.scalar(select(Project).where(Project.slug == slug))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/projects/{slug}/permissions", response_model=list[PermissionOut])
async def list_permissions(slug: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    result = await session.execute(select(Permission).where(Permission.project_id == project.id))
    return result.scalars().all()


@router.post("/projects/{slug}/permissions", response_model=PermissionOut, status_code=201)
async def create_permission(slug: str, body: PermissionCreate, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    perm = Permission(project_id=project.id, name=body.name, description=body.description)
    session.add(perm)
    await session.commit()
    await session.refresh(perm)
    return perm


@router.patch("/projects/{slug}/permissions/{perm_id}", response_model=PermissionOut)
async def update_permission(slug: str, perm_id: str, body: PermissionUpdate, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    perm = await session.scalar(select(Permission).where(Permission.id == perm_id, Permission.project_id == project.id))
    if not perm:
        raise HTTPException(404, "Permission not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(perm, field, value)
    await session.commit()
    await session.refresh(perm)
    return perm


@router.delete("/projects/{slug}/permissions/{perm_id}", status_code=204)
async def delete_permission(slug: str, perm_id: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    perm = await session.scalar(select(Permission).where(Permission.id == perm_id, Permission.project_id == project.id))
    if not perm:
        raise HTTPException(404, "Permission not found")
    await session.delete(perm)
    await session.commit()


@router.post("/projects/{slug}/roles/{role_id}/permissions/{perm_id}")
async def assign_permission(slug: str, role_id: str, perm_id: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    existing = await session.scalar(
        select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == perm_id)
    )
    if not existing:
        session.add(RolePermission(role_id=role_id, permission_id=perm_id))
        await session.commit()
    return {"ok": True}


@router.delete("/projects/{slug}/roles/{role_id}/permissions/{perm_id}", status_code=204)
async def unassign_permission(slug: str, role_id: str, perm_id: str, session: AsyncSession = Depends(get_session)):
    link = await session.scalar(
        select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == perm_id)
    )
    if link:
        await session.delete(link)
        await session.commit()


@router.post("/projects/{slug}/permissions/{perm_id}/resources/{res_id}")
async def map_resource(slug: str, perm_id: str, res_id: str, session: AsyncSession = Depends(get_session)):
    existing = await session.scalar(
        select(PermissionResource).where(PermissionResource.permission_id == perm_id, PermissionResource.resource_id == res_id)
    )
    if not existing:
        session.add(PermissionResource(permission_id=perm_id, resource_id=res_id))
        await session.commit()
    return {"ok": True}


@router.delete("/projects/{slug}/permissions/{perm_id}/resources/{res_id}", status_code=204)
async def unmap_resource(slug: str, perm_id: str, res_id: str, session: AsyncSession = Depends(get_session)):
    link = await session.scalar(
        select(PermissionResource).where(PermissionResource.permission_id == perm_id, PermissionResource.resource_id == res_id)
    )
    if link:
        await session.delete(link)
        await session.commit()
```

- [ ] **Step 5: Write resources.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Project, Resource
from app.schemas import ResourceCreate, ResourceUpdate, ResourceOut

router = APIRouter(tags=["resources"])


async def _get_project(slug: str, session: AsyncSession) -> Project:
    p = await session.scalar(select(Project).where(Project.slug == slug))
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("/projects/{slug}/resources", response_model=list[ResourceOut])
async def list_resources(slug: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    result = await session.execute(select(Resource).where(Resource.project_id == project.id))
    return result.scalars().all()


@router.post("/projects/{slug}/resources", response_model=ResourceOut, status_code=201)
async def create_resource(slug: str, body: ResourceCreate, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    res = Resource(project_id=project.id, method=body.method.upper(), path=body.path, description=body.description)
    session.add(res)
    await session.commit()
    await session.refresh(res)
    return res


@router.patch("/projects/{slug}/resources/{res_id}", response_model=ResourceOut)
async def update_resource(slug: str, res_id: str, body: ResourceUpdate, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    res = await session.scalar(select(Resource).where(Resource.id == res_id, Resource.project_id == project.id))
    if not res:
        raise HTTPException(404, "Resource not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(res, field, value.upper() if field == "method" else value)
    await session.commit()
    await session.refresh(res)
    return res


@router.delete("/projects/{slug}/resources/{res_id}", status_code=204)
async def delete_resource(slug: str, res_id: str, session: AsyncSession = Depends(get_session)):
    project = await _get_project(slug, session)
    res = await session.scalar(select(Resource).where(Resource.id == res_id, Resource.project_id == project.id))
    if not res:
        raise HTTPException(404, "Resource not found")
    await session.delete(res)
    await session.commit()
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
pytest tests/test_permissions.py tests/test_resources.py -v
```

Expected: 7 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/permissions.py backend/app/routers/resources.py backend/tests/
git commit -m "feat: add permissions and resources APIs with role/permission mapping"
```

---

## Task 7: Simulator API

**Files:**
- Create: `backend/app/routers/simulate.py`
- Create: `backend/tests/test_simulate.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_simulate.py
import pytest


@pytest.fixture
async def rbac(client):
    """Sets up: admin -> editor (inheritance), read_users perm -> GET /users resource, assigned to editor"""
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_admin = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_editor = await client.post("/api/v1/projects/test/roles", json={"name": "editor"})
    admin_id = r_admin.json()["id"]
    editor_id = r_editor.json()["id"]
    # editor inherits from admin
    await client.post(f"/api/v1/projects/test/roles/{editor_id}/parents", json={"parent_role_id": admin_id})
    # permission
    r_perm = await client.post("/api/v1/projects/test/permissions", json={"name": "read_users"})
    perm_id = r_perm.json()["id"]
    # resource
    r_res = await client.post("/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"})
    res_id = r_res.json()["id"]
    # map permission -> resource
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    # assign permission to admin role only
    await client.post(f"/api/v1/projects/test/roles/{admin_id}/permissions/{perm_id}")
    return {"admin_id": admin_id, "editor_id": editor_id, "perm_id": perm_id, "res_id": res_id}


async def test_simulate_direct_permission(client, rbac):
    r = await client.get(f"/api/v1/projects/test/simulate/{rbac['admin_id']}")
    assert r.status_code == 200
    data = r.json()
    allowed = [res for res in data["resources"] if res["allowed"]]
    assert any(res["path"] == "/users" for res in allowed)


async def test_simulate_inherited_permission(client, rbac):
    """Editor should have access to GET /users via inheritance from admin"""
    r = await client.get(f"/api/v1/projects/test/simulate/{rbac['editor_id']}")
    assert r.status_code == 200
    data = r.json()
    allowed = [res for res in data["resources"] if res["allowed"]]
    assert any(res["path"] == "/users" for res in allowed)


async def test_simulate_no_access(client, rbac):
    """A role with no permissions and no parents sees everything as denied"""
    r_viewer = await client.post("/api/v1/projects/test/roles", json={"name": "viewer"})
    viewer_id = r_viewer.json()["id"]
    r = await client.get(f"/api/v1/projects/test/simulate/{viewer_id}")
    assert r.status_code == 200
    denied = [res for res in r.json()["resources"] if not res["allowed"]]
    assert len(denied) == 1
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_simulate.py -v
```

Expected: all fail

- [ ] **Step 3: Write simulate.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_session
from app.models import Project, Role, Resource
from app.schemas import SimulateOut, SimulatedResource

router = APIRouter(tags=["simulate"])


@router.get("/projects/{slug}/simulate/{role_id}", response_model=SimulateOut)
async def simulate_role(slug: str, role_id: str, session: AsyncSession = Depends(get_session)):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")
    role = await session.scalar(select(Role).where(Role.id == role_id, Role.project_id == project.id))
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
            simulated.append(SimulatedResource(
                resource_id=res.id,
                method=res.method,
                path=res.path,
                allowed=True,
                granted_by_permission=row.permission_name,
                granted_by_role=row.role_name,
            ))
        else:
            simulated.append(SimulatedResource(
                resource_id=res.id,
                method=res.method,
                path=res.path,
                allowed=False,
            ))

    return SimulateOut(role_id=role_id, role_name=role.name, resources=simulated)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_simulate.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/simulate.py backend/tests/test_simulate.py
git commit -m "feat: add simulator API with recursive CTE for inherited access resolution"
```

---

## Task 8: Analyze + Export + Import APIs

**Files:**
- Create: `backend/app/routers/analyze.py`
- Create: `backend/app/routers/export.py`
- Create: `backend/app/routers/import_.py`
- Create: `backend/tests/test_analyze.py`
- Create: `backend/tests/test_export.py`
- Create: `backend/tests/test_import.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_analyze.py
import pytest


@pytest.fixture
async def project_with_orphan(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    # orphaned permission — not assigned to any role
    await client.post("/api/v1/projects/test/permissions", json={"name": "orphaned_perm"})


async def test_detects_orphaned_permission(client, project_with_orphan):
    r = await client.get("/api/v1/projects/test/analyze")
    assert r.status_code == 200
    findings = r.json()["findings"]
    assert any(f["type"] == "orphaned_permission" for f in findings)


async def test_detects_empty_role(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    await client.post("/api/v1/projects/test/roles", json={"name": "empty"})
    r = await client.get("/api/v1/projects/test/analyze")
    findings = r.json()["findings"]
    assert any(f["type"] == "empty_role" for f in findings)
```

```python
# backend/tests/test_export.py
import pytest


@pytest.fixture
async def setup(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_role = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post("/api/v1/projects/test/permissions", json={"name": "read_users"})
    r_res = await client.post("/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"})
    perm_id = r_perm.json()["id"]
    res_id = r_res.json()["id"]
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")


async def test_export_fastapi_contains_route_stub(client, setup):
    r = await client.get("/api/v1/projects/test/export/fastapi")
    assert r.status_code == 200
    code = r.text
    assert "require_permission" in code
    assert "/users" in code
    assert "read_users" in code
```

```python
# backend/tests/test_import.py
import pytest, json


async def test_import_openapi_creates_resources(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    openapi = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {"get": {}, "post": {}},
            "/users/{id}": {"get": {}, "delete": {}},
        }
    }
    r = await client.post("/api/v1/projects/test/import/openapi", json=openapi)
    assert r.status_code == 200
    assert r.json()["created"] == 4
    # second import skips existing
    r2 = await client.post("/api/v1/projects/test/import/openapi", json=openapi)
    assert r2.json()["skipped"] == 4
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_analyze.py tests/test_export.py tests/test_import.py -v
```

Expected: all fail

- [ ] **Step 3: Write analyze.py**

```python
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
```

- [ ] **Step 4: Write export.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import get_session
from app.models import Project

router = APIRouter(tags=["export"])


@router.get("/projects/{slug}/export/fastapi", response_class=PlainTextResponse)
async def export_fastapi(slug: str, session: AsyncSession = Depends(get_session)):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")

    result = await session.execute(text("""
        SELECT DISTINCT res.method, res.path, p.name AS permission_name
        FROM resources res
        JOIN permission_resources pr ON pr.resource_id = res.id
        JOIN permissions p ON p.id = pr.permission_id
        WHERE res.project_id = :pid
        ORDER BY res.path, res.method
    """), {"pid": project.id})
    rows = result.fetchall()

    lines = [
        f"# Generated by RBACExplorer — {project.name}",
        "from fastapi import APIRouter, Depends, HTTPException",
        "from typing import Callable",
        "",
        "router = APIRouter()",
        "",
        "",
        "def require_permission(permission: str) -> Callable:",
        '    """Replace get_current_user_permissions with your own auth logic."""',
        "    def dependency(current_permissions: list[str] = Depends(get_current_user_permissions)):",
        "        if permission not in current_permissions:",
        '            raise HTTPException(status_code=403, detail="Forbidden")',
        "    return dependency",
        "",
        "",
        "# --- Route stubs ---",
        "",
    ]

    for row in rows:
        method = row.method.lower()
        safe_path = row.path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
        func_name = f"{method}_{safe_path}" if safe_path else method
        lines += [
            f'@router.{method}("{row.path}")',
            f'async def {func_name}(_=Depends(require_permission("{row.permission_name}"))):\n    ...',
            "",
        ]

    return "\n".join(lines)
```

- [ ] **Step 5: Write import_.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models import Project, Resource

router = APIRouter(tags=["import"])

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete"}


@router.post("/projects/{slug}/import/openapi")
async def import_openapi(slug: str, body: dict, session: AsyncSession = Depends(get_session)):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")

    paths = body.get("paths", {})
    created = 0
    skipped = 0

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
                session.add(Resource(project_id=project.id, method=method.upper(), path=path))
                created += 1

    await session.commit()
    return {"created": created, "skipped": skipped}
```

- [ ] **Step 6: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/analyze.py backend/app/routers/export.py backend/app/routers/import_.py backend/tests/
git commit -m "feat: add analyze, export, and import APIs — backend complete"
```

---

## Task 9: Frontend scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/vercel.json`

- [ ] **Step 1: Scaffold Vite + React project**

```bash
cd /Users/aishitdua/Code/RBACExplorer
npm create vite@latest frontend -- --template react
cd frontend && npm install
npm install axios react-router-dom cytoscape cytoscape-fcose
npm install -D tailwindcss @tailwindcss/vite vitest @testing-library/react @testing-library/jest-dom @vitejs/plugin-react jsdom
npx tailwindcss init
```

- [ ] **Step 2: Configure vite.config.js**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.js',
  },
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: Create src/test-setup.js**

```js
import '@testing-library/jest-dom'
```

- [ ] **Step 4: Create src/index.css** (Tailwind directives)

```css
@import "tailwindcss";
```

- [ ] **Step 5: Create src/main.jsx**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 6: Create src/App.jsx**

```jsx
import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import WorkspacePage from './pages/WorkspacePage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/:slug" element={<WorkspacePage />} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 7: Create vercel.json** (SPA routing)

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

- [ ] **Step 8: Create frontend/.env.example**

```
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 9: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Expected: Vite running on http://localhost:5173

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold React frontend with Vite, Tailwind, and React Router"
```

---

## Task 10: API client layer

**Files:**
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/api/projects.js`
- Create: `frontend/src/api/roles.js`
- Create: `frontend/src/api/permissions.js`
- Create: `frontend/src/api/resources.js`
- Create: `frontend/src/api/simulate.js`
- Create: `frontend/src/api/analyze.js`
- Create: `frontend/src/api/export_.js`
- Create: `frontend/src/api/import_.js`

- [ ] **Step 1: Write failing test for API client**

```js
// frontend/src/api/projects.test.js
import { describe, it, expect, vi, beforeEach } from 'vitest'
import client from './client'
import { createProject, getProject } from './projects'

vi.mock('./client')

describe('projects API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('createProject posts to /api/v1/projects', async () => {
    client.post = vi.fn().mockResolvedValue({ data: { slug: 'my-app', name: 'My App' } })
    const result = await createProject({ name: 'My App' })
    expect(client.post).toHaveBeenCalledWith('/api/v1/projects', { name: 'My App' })
    expect(result.slug).toBe('my-app')
  })

  it('getProject fetches by slug', async () => {
    client.get = vi.fn().mockResolvedValue({ data: { slug: 'my-app' } })
    const result = await getProject('my-app')
    expect(client.get).toHaveBeenCalledWith('/api/v1/projects/my-app')
    expect(result.slug).toBe('my-app')
  })
})
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd frontend && npx vitest run src/api/projects.test.js
```

Expected: FAIL — module not found

- [ ] **Step 3: Write client.js**

```js
import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

export default client
```

- [ ] **Step 4: Write projects.js**

```js
import client from './client'

export const createProject = async (data) => (await client.post('/api/v1/projects', data)).data
export const getProject = async (slug) => (await client.get(`/api/v1/projects/${slug}`)).data
export const deleteProject = async (slug) => client.delete(`/api/v1/projects/${slug}`)
```

- [ ] **Step 5: Write roles.js**

```js
import client from './client'

export const listRoles = async (slug) => (await client.get(`/api/v1/projects/${slug}/roles`)).data
export const createRole = async (slug, data) => (await client.post(`/api/v1/projects/${slug}/roles`, data)).data
export const updateRole = async (slug, id, data) => (await client.patch(`/api/v1/projects/${slug}/roles/${id}`, data)).data
export const deleteRole = async (slug, id) => client.delete(`/api/v1/projects/${slug}/roles/${id}`)
export const addParent = async (slug, roleId, parentRoleId) =>
  client.post(`/api/v1/projects/${slug}/roles/${roleId}/parents`, { parent_role_id: parentRoleId })
export const removeParent = async (slug, roleId, parentId) =>
  client.delete(`/api/v1/projects/${slug}/roles/${roleId}/parents/${parentId}`)
```

- [ ] **Step 6: Write permissions.js**

```js
import client from './client'

export const listPermissions = async (slug) => (await client.get(`/api/v1/projects/${slug}/permissions`)).data
export const createPermission = async (slug, data) => (await client.post(`/api/v1/projects/${slug}/permissions`, data)).data
export const updatePermission = async (slug, id, data) => (await client.patch(`/api/v1/projects/${slug}/permissions/${id}`, data)).data
export const deletePermission = async (slug, id) => client.delete(`/api/v1/projects/${slug}/permissions/${id}`)
export const assignPermissionToRole = async (slug, roleId, permId) =>
  client.post(`/api/v1/projects/${slug}/roles/${roleId}/permissions/${permId}`)
export const unassignPermissionFromRole = async (slug, roleId, permId) =>
  client.delete(`/api/v1/projects/${slug}/roles/${roleId}/permissions/${permId}`)
export const mapPermissionToResource = async (slug, permId, resId) =>
  client.post(`/api/v1/projects/${slug}/permissions/${permId}/resources/${resId}`)
export const unmapPermissionFromResource = async (slug, permId, resId) =>
  client.delete(`/api/v1/projects/${slug}/permissions/${permId}/resources/${resId}`)
```

- [ ] **Step 7: Write resources.js, simulate.js, analyze.js, export_.js, import_.js**

```js
// resources.js
import client from './client'
export const listResources = async (slug) => (await client.get(`/api/v1/projects/${slug}/resources`)).data
export const createResource = async (slug, data) => (await client.post(`/api/v1/projects/${slug}/resources`, data)).data
export const updateResource = async (slug, id, data) => (await client.patch(`/api/v1/projects/${slug}/resources/${id}`, data)).data
export const deleteResource = async (slug, id) => client.delete(`/api/v1/projects/${slug}/resources/${id}`)
```

```js
// simulate.js
import client from './client'
export const simulateRole = async (slug, roleId) => (await client.get(`/api/v1/projects/${slug}/simulate/${roleId}`)).data
```

```js
// analyze.js
import client from './client'
export const analyzeProject = async (slug) => (await client.get(`/api/v1/projects/${slug}/analyze`)).data
```

```js
// export_.js
import client from './client'
export const exportFastapi = async (slug) => (await client.get(`/api/v1/projects/${slug}/export/fastapi`)).data
```

```js
// import_.js
import client from './client'
export const importOpenapi = async (slug, openapiJson) =>
  (await client.post(`/api/v1/projects/${slug}/import/openapi`, openapiJson)).data
```

- [ ] **Step 8: Run API client tests**

```bash
npx vitest run src/api/
```

Expected: all pass

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api/
git commit -m "feat: add typed API client layer for all backend endpoints"
```

---

## Task 11: Home page + Workspace shell

**Files:**
- Create: `frontend/src/pages/HomePage.jsx`
- Create: `frontend/src/pages/WorkspacePage.jsx`

- [ ] **Step 1: Write failing test for HomePage**

```jsx
// frontend/src/pages/HomePage.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import HomePage from './HomePage'
import * as projectsApi from '../api/projects'

vi.mock('../api/projects')

describe('HomePage', () => {
  it('renders create project form', () => {
    render(<MemoryRouter><HomePage /></MemoryRouter>)
    expect(screen.getByPlaceholderText(/project name/i)).toBeInTheDocument()
  })

  it('creates a project and redirects', async () => {
    projectsApi.createProject.mockResolvedValue({ slug: 'my-app', name: 'My App' })
    render(<MemoryRouter><HomePage /></MemoryRouter>)
    fireEvent.change(screen.getByPlaceholderText(/project name/i), { target: { value: 'My App' } })
    fireEvent.click(screen.getByRole('button', { name: /create/i }))
    await waitFor(() => expect(projectsApi.createProject).toHaveBeenCalledWith({ name: 'My App', description: '' }))
  })
})
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx vitest run src/pages/HomePage.test.jsx
```

Expected: FAIL — component not found

- [ ] **Step 3: Write HomePage.jsx**

```jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createProject } from '../api/projects'

export default function HomePage() {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [slug, setSlug] = useState('')
  const [openSlug, setOpenSlug] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleCreate = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const project = await createProject({ name, description })
      navigate(`/${project.slug}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white">RBACExplorer</h1>
          <p className="mt-2 text-gray-400">Design and visualise your app's access control</p>
        </div>

        <form onSubmit={handleCreate} className="space-y-4 bg-gray-900 p-6 rounded-xl border border-gray-800">
          <h2 className="text-lg font-semibold text-white">Create a project</h2>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="Project name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
          >
            Create project
          </button>
        </form>

        <div className="bg-gray-900 p-6 rounded-xl border border-gray-800 space-y-4">
          <h2 className="text-lg font-semibold text-white">Open existing project</h2>
          <div className="flex gap-2">
            <input
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
              placeholder="Project slug"
              value={openSlug}
              onChange={(e) => setOpenSlug(e.target.value)}
            />
            <button
              onClick={() => openSlug && navigate(`/${openSlug}`)}
              className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Open
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Write WorkspacePage.jsx**

```jsx
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getProject } from '../api/projects'
import GraphTab from '../tabs/GraphTab'
import RolesTab from '../tabs/RolesTab'
import PermissionsTab from '../tabs/PermissionsTab'
import ResourcesTab from '../tabs/ResourcesTab'
import SimulatorTab from '../tabs/SimulatorTab'

const TABS = ['Graph', 'Roles', 'Permissions', 'Resources', 'Simulator']

export default function WorkspacePage() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [activeTab, setActiveTab] = useState('Graph')
  const [error, setError] = useState('')

  useEffect(() => {
    getProject(slug)
      .then(setProject)
      .catch(() => setError('Project not found'))
  }, [slug])

  if (error) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center space-y-4">
        <p className="text-red-400">{error}</p>
        <button onClick={() => navigate('/')} className="text-blue-400 hover:underline">Go home</button>
      </div>
    </div>
  )

  if (!project) return <div className="flex items-center justify-center min-h-screen text-gray-500">Loading...</div>

  return (
    <div className="flex flex-col h-screen">
      <header className="flex items-center gap-6 px-6 py-3 bg-gray-900 border-b border-gray-800">
        <button onClick={() => navigate('/')} className="text-gray-400 hover:text-white text-sm">← Home</button>
        <h1 className="text-white font-semibold">{project.name}</h1>
        <span className="text-gray-500 text-sm font-mono">{slug}</span>
        <nav className="ml-auto flex gap-1">
          {TABS.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>
      <main className="flex-1 overflow-hidden">
        {activeTab === 'Graph' && <GraphTab slug={slug} />}
        {activeTab === 'Roles' && <RolesTab slug={slug} />}
        {activeTab === 'Permissions' && <PermissionsTab slug={slug} />}
        {activeTab === 'Resources' && <ResourcesTab slug={slug} />}
        {activeTab === 'Simulator' && <SimulatorTab slug={slug} />}
      </main>
    </div>
  )
}
```

- [ ] **Step 5: Run tests**

```bash
npx vitest run src/pages/HomePage.test.jsx
```

Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat: add home page and workspace tab shell"
```

---

## Task 12: Roles, Permissions, Resources tabs

**Files:**
- Create: `frontend/src/tabs/RolesTab.jsx`
- Create: `frontend/src/tabs/PermissionsTab.jsx`
- Create: `frontend/src/tabs/ResourcesTab.jsx`
- Create: `frontend/src/components/OpenAPIImportModal.jsx`

- [ ] **Step 1: Write failing test for RolesTab**

```jsx
// frontend/src/tabs/RolesTab.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import RolesTab from './RolesTab'
import * as rolesApi from '../api/roles'

vi.mock('../api/roles')

describe('RolesTab', () => {
  it('renders role list', async () => {
    rolesApi.listRoles.mockResolvedValue([
      { id: '1', name: 'admin', description: '', color: '#60a5fa' },
      { id: '2', name: 'viewer', description: '', color: '#34d399' },
    ])
    render(<RolesTab slug="test" />)
    await waitFor(() => expect(screen.getByText('admin')).toBeInTheDocument())
    expect(screen.getByText('viewer')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx vitest run src/tabs/RolesTab.test.jsx
```

Expected: FAIL

- [ ] **Step 3: Write RolesTab.jsx**

```jsx
import { useState, useEffect } from 'react'
import { listRoles, createRole, deleteRole } from '../api/roles'

export default function RolesTab({ slug }) {
  const [roles, setRoles] = useState([])
  const [name, setName] = useState('')
  const [color, setColor] = useState('#60a5fa')
  const [error, setError] = useState('')

  const load = () => listRoles(slug).then(setRoles).catch(() => setError('Failed to load roles'))

  useEffect(() => { load() }, [slug])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await createRole(slug, { name, color })
      setName('')
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create role')
    }
  }

  const handleDelete = async (id) => {
    await deleteRole(slug, id)
    load()
  }

  return (
    <div className="p-6 space-y-6">
      <form onSubmit={handleCreate} className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="block text-sm text-gray-400 mb-1">Role name</label>
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="e.g. admin"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Color</label>
          <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-10 w-16 rounded cursor-pointer bg-gray-800 border border-gray-700" />
        </div>
        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Add role</button>
      </form>
      {error && <p className="text-red-400 text-sm">{error}</p>}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-2">Name</th>
            <th className="text-left py-2">Color</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {roles.map(role => (
            <tr key={role.id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="py-2 text-white font-mono">{role.name}</td>
              <td className="py-2">
                <span className="inline-block w-4 h-4 rounded-full" style={{ backgroundColor: role.color }} />
              </td>
              <td className="py-2 text-right">
                <button onClick={() => handleDelete(role.id)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4: Write PermissionsTab.jsx**

```jsx
import { useState, useEffect } from 'react'
import { listPermissions, createPermission, deletePermission, assignPermissionToRole, mapPermissionToResource } from '../api/permissions'
import { listRoles } from '../api/roles'
import { listResources } from '../api/resources'

export default function PermissionsTab({ slug }) {
  const [permissions, setPermissions] = useState([])
  const [roles, setRoles] = useState([])
  const [resources, setResources] = useState([])
  const [name, setName] = useState('')

  const load = () => Promise.all([
    listPermissions(slug).then(setPermissions),
    listRoles(slug).then(setRoles),
    listResources(slug).then(setResources),
  ])

  useEffect(() => { load() }, [slug])

  const handleCreate = async (e) => {
    e.preventDefault()
    await createPermission(slug, { name })
    setName('')
    load()
  }

  return (
    <div className="p-6 space-y-6">
      <form onSubmit={handleCreate} className="flex gap-3">
        <input
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          placeholder="e.g. read_users"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Add permission</button>
      </form>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-2">Permission</th>
            <th className="text-left py-2">Assign to role</th>
            <th className="text-left py-2">Map to endpoint</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {permissions.map(perm => (
            <tr key={perm.id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="py-2 text-white font-mono">{perm.name}</td>
              <td className="py-2">
                <select
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                  onChange={(e) => e.target.value && assignPermissionToRole(slug, e.target.value, perm.id)}
                  defaultValue=""
                >
                  <option value="">Assign to role…</option>
                  {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
              </td>
              <td className="py-2">
                <select
                  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                  onChange={(e) => e.target.value && mapPermissionToResource(slug, perm.id, e.target.value)}
                  defaultValue=""
                >
                  <option value="">Map to endpoint…</option>
                  {resources.map(r => <option key={r.id} value={r.id}>{r.method} {r.path}</option>)}
                </select>
              </td>
              <td className="py-2 text-right">
                <button onClick={() => deletePermission(slug, perm.id).then(load)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 5: Write OpenAPIImportModal.jsx**

```jsx
import { useState } from 'react'
import { importOpenapi } from '../api/import_'

export default function OpenAPIImportModal({ slug, onClose, onImported }) {
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleImport = async () => {
    setError('')
    try {
      const json = JSON.parse(text)
      const res = await importOpenapi(slug, json)
      setResult(res)
      onImported()
    } catch (err) {
      setError(err.message || 'Invalid JSON or import failed')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-lg space-y-4">
        <h2 className="text-white font-semibold">Import from OpenAPI spec</h2>
        <p className="text-gray-400 text-sm">Paste your OpenAPI 3.x JSON below. All paths and methods will be imported as resources.</p>
        <textarea
          className="w-full h-48 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-blue-500"
          placeholder='{ "openapi": "3.0.0", "paths": { ... } }'
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        {error && <p className="text-red-400 text-sm">{error}</p>}
        {result && <p className="text-green-400 text-sm">Created {result.created}, skipped {result.skipped}</p>}
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="text-gray-400 hover:text-white px-4 py-2">Cancel</button>
          <button onClick={handleImport} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Import</button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Write ResourcesTab.jsx**

```jsx
import { useState, useEffect } from 'react'
import { listResources, createResource, deleteResource } from '../api/resources'
import OpenAPIImportModal from '../components/OpenAPIImportModal'

const METHOD_COLORS = { GET: 'text-green-400', POST: 'text-blue-400', PUT: 'text-yellow-400', PATCH: 'text-orange-400', DELETE: 'text-red-400' }

export default function ResourcesTab({ slug }) {
  const [resources, setResources] = useState([])
  const [method, setMethod] = useState('GET')
  const [path, setPath] = useState('')
  const [showImport, setShowImport] = useState(false)

  const load = () => listResources(slug).then(setResources)
  useEffect(() => { load() }, [slug])

  const handleCreate = async (e) => {
    e.preventDefault()
    await createResource(slug, { method, path })
    setPath('')
    load()
  }

  return (
    <div className="p-6 space-y-6">
      {showImport && <OpenAPIImportModal slug={slug} onClose={() => setShowImport(false)} onImported={load} />}
      <div className="flex gap-3 justify-between items-end">
        <form onSubmit={handleCreate} className="flex gap-3 flex-1">
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
          >
            {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map(m => <option key={m}>{m}</option>)}
          </select>
          <input
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            placeholder="/users/{id}"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            required
          />
          <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Add</button>
        </form>
        <button onClick={() => setShowImport(true)} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm">Import OpenAPI</button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 border-b border-gray-800">
            <th className="text-left py-2">Method</th>
            <th className="text-left py-2">Path</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {resources.map(res => (
            <tr key={res.id} className="border-b border-gray-800 hover:bg-gray-900">
              <td className="py-2">
                <span className={`font-mono font-bold text-xs ${METHOD_COLORS[res.method] || 'text-gray-400'}`}>{res.method}</span>
              </td>
              <td className="py-2 text-white font-mono">{res.path}</td>
              <td className="py-2 text-right">
                <button onClick={() => deleteResource(slug, res.id).then(load)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 7: Run RolesTab test**

```bash
npx vitest run src/tabs/RolesTab.test.jsx
```

Expected: 1 passed

- [ ] **Step 8: Commit**

```bash
git add frontend/src/tabs/ frontend/src/components/OpenAPIImportModal.jsx
git commit -m "feat: add Roles, Permissions, Resources tabs with OpenAPI import"
```

---

## Task 13: Graph tab (Cytoscape.js)

**Files:**
- Create: `frontend/src/tabs/GraphTab.jsx`

- [ ] **Step 1: Write failing test**

```jsx
// frontend/src/tabs/GraphTab.test.jsx
import { render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'
import GraphTab from './GraphTab'
import * as rolesApi from '../api/roles'
import * as permissionsApi from '../api/permissions'

vi.mock('../api/roles')
vi.mock('../api/permissions')

// Cytoscape is a DOM library — mock it for unit tests
vi.mock('cytoscape', () => ({ default: vi.fn(() => ({ add: vi.fn(), layout: vi.fn(() => ({ run: vi.fn() })), on: vi.fn(), destroy: vi.fn() })) }))
vi.mock('cytoscape-fcose', () => ({ default: vi.fn() }))

describe('GraphTab', () => {
  it('renders graph container', async () => {
    rolesApi.listRoles.mockResolvedValue([])
    permissionsApi.listPermissions.mockResolvedValue([])
    render(<GraphTab slug="test" />)
    await waitFor(() => expect(document.getElementById('cy')).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx vitest run src/tabs/GraphTab.test.jsx
```

Expected: FAIL

- [ ] **Step 3: Write GraphTab.jsx**

```jsx
import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { listRoles } from '../api/roles'
import { listPermissions } from '../api/permissions'

cytoscape.use(fcose)

export default function GraphTab({ slug }) {
  const cyRef = useRef(null)
  const containerRef = useRef(null)
  const [selected, setSelected] = useState(null)
  const [showPermissions, setShowPermissions] = useState(false)

  useEffect(() => {
    let cy
    Promise.all([listRoles(slug), listPermissions(slug)]).then(([roles, permissions]) => {
      const elements = []

      // Role nodes
      roles.forEach(role => {
        elements.push({
          data: { id: role.id, label: role.name, type: 'role', color: role.color },
        })
      })

      // Placeholder: role_inheritance edges come from role detail API
      // For now render roles only — edges added when backend returns parents
      roles.forEach(role => {
        if (role.parents) {
          role.parents.forEach(parentId => {
            elements.push({ data: { id: `${parentId}-${role.id}`, source: parentId, target: role.id, type: 'inheritance' } })
          })
        }
      })

      cy = cytoscape({
        container: containerRef.current,
        elements,
        style: [
          {
            selector: 'node[type="role"]',
            style: {
              label: 'data(label)',
              'background-color': 'data(color)',
              color: '#fff',
              'text-valign': 'center',
              'font-family': 'monospace',
              'font-size': '12px',
              width: 60,
              height: 60,
              'border-width': 2,
              'border-color': '#1e293b',
            },
          },
          {
            selector: 'edge[type="inheritance"]',
            style: {
              width: 2,
              'line-color': '#334155',
              'target-arrow-color': '#334155',
              'target-arrow-shape': 'triangle',
              'curve-style': 'bezier',
            },
          },
          {
            selector: ':selected',
            style: { 'border-color': '#60a5fa', 'border-width': 3 },
          },
        ],
        layout: { name: 'fcose', animate: true, randomize: false, nodeRepulsion: 4500 },
      })

      cyRef.current = cy

      cy.on('tap', 'node', (e) => {
        const node = e.target
        setSelected({ id: node.id(), label: node.data('label'), type: node.data('type') })
      })

      cy.on('tap', (e) => {
        if (e.target === cy) setSelected(null)
      })
    })

    return () => { if (cyRef.current) cyRef.current.destroy() }
  }, [slug])

  return (
    <div className="relative h-full">
      <div id="cy" ref={containerRef} className="w-full h-full bg-gray-950" />
      <div className="absolute top-4 left-4 flex gap-2">
        <button
          onClick={() => setShowPermissions(v => !v)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${showPermissions ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'}`}
        >
          Show permissions
        </button>
      </div>
      {selected && (
        <div className="absolute top-4 right-4 bg-gray-900 border border-gray-700 rounded-xl p-4 w-64 space-y-2">
          <h3 className="text-white font-semibold font-mono">{selected.label}</h3>
          <p className="text-gray-400 text-xs capitalize">{selected.type}</p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test**

```bash
npx vitest run src/tabs/GraphTab.test.jsx
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add frontend/src/tabs/GraphTab.jsx
git commit -m "feat: add force-directed role hierarchy graph with Cytoscape.js fcose"
```

---

## Task 14: Simulator tab + Code export modal

**Files:**
- Create: `frontend/src/tabs/SimulatorTab.jsx`
- Create: `frontend/src/components/CodeExportModal.jsx`
- Create: `frontend/src/components/ConflictPanel.jsx`

- [ ] **Step 1: Write failing test**

```jsx
// frontend/src/tabs/SimulatorTab.test.jsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import SimulatorTab from './SimulatorTab'
import * as rolesApi from '../api/roles'
import * as simulateApi from '../api/simulate'
import * as analyzeApi from '../api/analyze'

vi.mock('../api/roles')
vi.mock('../api/simulate')
vi.mock('../api/analyze')

describe('SimulatorTab', () => {
  it('shows allowed and denied resources after selecting a role', async () => {
    rolesApi.listRoles.mockResolvedValue([{ id: '1', name: 'admin', color: '#60a5fa' }])
    analyzeApi.analyzeProject.mockResolvedValue({ findings: [] })
    simulateApi.simulateRole.mockResolvedValue({
      role_id: '1',
      role_name: 'admin',
      resources: [
        { resource_id: 'r1', method: 'GET', path: '/users', allowed: true, granted_by_permission: 'read_users', granted_by_role: 'admin' },
        { resource_id: 'r2', method: 'DELETE', path: '/users/{id}', allowed: false },
      ],
    })
    render(<SimulatorTab slug="test" />)
    await waitFor(() => screen.getByText('admin'))
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })
    await waitFor(() => expect(screen.getByText('/users')).toBeInTheDocument())
    expect(screen.getByText('ALLOWED')).toBeInTheDocument()
    expect(screen.getByText('DENIED')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test — verify it fails**

```bash
npx vitest run src/tabs/SimulatorTab.test.jsx
```

Expected: FAIL

- [ ] **Step 3: Write ConflictPanel.jsx**

```jsx
const TYPE_LABELS = {
  orphaned_permission: 'Orphaned permission',
  empty_role: 'Empty role',
  redundant_assignment: 'Redundant assignment',
  permission_shadowing: 'Permission shadowing',
  circular_inheritance: 'Circular inheritance',
}

export default function ConflictPanel({ findings }) {
  if (!findings.length) return (
    <div className="text-green-400 text-sm py-2">No conflicts detected</div>
  )

  return (
    <div className="space-y-2">
      {findings.map((f, i) => (
        <div key={i} className="flex items-start gap-3 bg-yellow-950/40 border border-yellow-800/40 rounded-lg px-4 py-3">
          <span className="text-yellow-400 mt-0.5">⚠</span>
          <div>
            <p className="text-yellow-300 text-sm font-medium">{TYPE_LABELS[f.type] || f.type}</p>
            <p className="text-yellow-600 text-xs mt-0.5">{Object.entries(f.detail).map(([k, v]) => `${k}: ${v}`).join(' · ')}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Write CodeExportModal.jsx**

```jsx
import { useState, useEffect } from 'react'
import { exportFastapi } from '../api/export_'

export default function CodeExportModal({ slug, onClose }) {
  const [code, setCode] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    exportFastapi(slug).then(setCode)
  }, [slug])

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-white font-semibold">FastAPI code export</h2>
          <div className="flex gap-2">
            <button onClick={handleCopy} className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded-lg text-sm">
              {copied ? 'Copied!' : 'Copy'}
            </button>
            <button onClick={onClose} className="text-gray-400 hover:text-white px-3 py-1.5">Close</button>
          </div>
        </div>
        <pre className="bg-gray-950 border border-gray-800 rounded-lg p-4 text-xs text-gray-300 font-mono overflow-auto max-h-96 whitespace-pre-wrap">{code}</pre>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Write SimulatorTab.jsx**

```jsx
import { useState, useEffect } from 'react'
import { listRoles } from '../api/roles'
import { simulateRole } from '../api/simulate'
import { analyzeProject } from '../api/analyze'
import ConflictPanel from '../components/ConflictPanel'
import CodeExportModal from '../components/CodeExportModal'

const METHOD_COLORS = { GET: 'text-green-400', POST: 'text-blue-400', PUT: 'text-yellow-400', PATCH: 'text-orange-400', DELETE: 'text-red-400' }

export default function SimulatorTab({ slug }) {
  const [roles, setRoles] = useState([])
  const [selectedRoleId, setSelectedRoleId] = useState('')
  const [simulation, setSimulation] = useState(null)
  const [findings, setFindings] = useState([])
  const [showExport, setShowExport] = useState(false)

  useEffect(() => {
    listRoles(slug).then(setRoles)
    analyzeProject(slug).then(r => setFindings(r.findings))
  }, [slug])

  const handleRoleChange = async (e) => {
    const roleId = e.target.value
    setSelectedRoleId(roleId)
    if (roleId) {
      const result = await simulateRole(slug, roleId)
      setSimulation(result)
    } else {
      setSimulation(null)
    }
  }

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {showExport && <CodeExportModal slug={slug} onClose={() => setShowExport(false)} />}
      <div className="flex gap-4 items-center">
        <div className="flex-1">
          <label className="block text-sm text-gray-400 mb-1">Simulate access as role</label>
          <select
            value={selectedRoleId}
            onChange={handleRoleChange}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-full"
          >
            <option value="">Select a role…</option>
            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <button
          onClick={() => setShowExport(true)}
          className="mt-5 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm"
        >
          Export FastAPI code
        </button>
      </div>

      {simulation && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-2">Method</th>
              <th className="text-left py-2">Path</th>
              <th className="text-left py-2">Access</th>
              <th className="text-left py-2">Granted by</th>
            </tr>
          </thead>
          <tbody>
            {simulation.resources.map(res => (
              <tr key={res.resource_id} className="border-b border-gray-800 hover:bg-gray-900">
                <td className="py-2">
                  <span className={`font-mono font-bold text-xs ${METHOD_COLORS[res.method] || 'text-gray-400'}`}>{res.method}</span>
                </td>
                <td className="py-2 text-white font-mono">{res.path}</td>
                <td className="py-2">
                  {res.allowed
                    ? <span className="text-green-400 font-semibold text-xs">ALLOWED</span>
                    : <span className="text-red-400 font-semibold text-xs">DENIED</span>}
                </td>
                <td className="py-2 text-gray-500 text-xs">
                  {res.allowed ? `${res.granted_by_permission} (via ${res.granted_by_role})` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-3">Conflicts & Anomalies</h3>
        <ConflictPanel findings={findings} />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Run test**

```bash
npx vitest run src/tabs/SimulatorTab.test.jsx
```

Expected: 1 passed

- [ ] **Step 7: Run full frontend test suite**

```bash
npx vitest run
```

Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add frontend/src/tabs/SimulatorTab.jsx frontend/src/components/
git commit -m "feat: add simulator tab, conflict panel, and FastAPI code export modal"
```

---

## Task 15: Alembic migrations + Neon wiring

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py` (generated then modified)

- [ ] **Step 1: Initialise Alembic**

```bash
cd backend && source venv/bin/activate
alembic init alembic
```

- [ ] **Step 2: Edit alembic/env.py — replace content**

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.database import Base
from app import models  # noqa: F401 — ensures models register with Base

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.config_options, prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Edit alembic.ini — set sqlalchemy.url**

Change line:
```
sqlalchemy.url = driver://user:pass@localhost/dbname
```
To:
```
sqlalchemy.url = %(DATABASE_URL)s
```

Then add to `[alembic]` section:
```
[alembic]
...
script_location = alembic
prepend_sys_path = .
```

- [ ] **Step 4: Generate initial migration**

```bash
DATABASE_URL=postgresql+psycopg2://user:pass@host/db alembic revision --autogenerate -m "initial schema"
```

(Use your actual Neon sync URL here — Alembic needs a sync driver. Add `psycopg2-binary` to requirements.txt for migration runs only.)

- [ ] **Step 5: Apply migration to Neon**

```bash
DATABASE_URL=postgresql+psycopg2://user:pass@host/db alembic upgrade head
```

Expected: all 7 tables created in Neon

- [ ] **Step 6: Create .env with your Neon async URL**

```
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require
```

- [ ] **Step 7: Smoke test backend against Neon**

```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 8: Commit**

```bash
git add backend/alembic/ backend/alembic.ini backend/requirements.txt
git commit -m "feat: add Alembic migrations, wired to Neon Postgres"
```

---

## Task 16: Deployment

**Files:**
- Create: `backend/render.yaml`
- Create: `frontend/vercel.json` (already done in Task 9)
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Write render.yaml**

```yaml
services:
  - type: web
    name: rbacexplorer-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
    healthCheckPath: /health
```

- [ ] **Step 2: Push to GitHub**

```bash
git remote -v  # verify origin is set to git@github.com:aishitdua/RBACExplorer.git
git push origin main
```

- [ ] **Step 3: Deploy backend to Render**

1. Go to https://render.com → New → Web Service
2. Connect the GitHub repo
3. Set root directory: `backend`
4. Add environment variable: `DATABASE_URL` = your Neon `postgresql+asyncpg://...` URL
5. Deploy

- [ ] **Step 4: Deploy frontend to Vercel**

1. Go to https://vercel.com → New Project → import RBACExplorer repo
2. Set root directory: `frontend`
3. Add environment variable: `VITE_API_URL` = your Render service URL (e.g. `https://rbacexplorer-api.onrender.com`)
4. Deploy

- [ ] **Step 5: Smoke test live deployment**

```bash
curl https://rbacexplorer-api.onrender.com/health
```

Expected: `{"status":"ok"}`

Open the Vercel URL → create a project → add roles → visit the Graph tab

- [ ] **Step 6: Final commit**

```bash
git add backend/render.yaml
git commit -m "chore: add Render deployment config"
git push origin main
```

---

## Task 17: Policy Diff API (optional — build after core is working)

**Files:**
- Modify: `backend/app/routers/analyze.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_diff.py`

The diff endpoint answers: "If I make these changes to a role, what access changes?" It is a pure read — no mutation. Pass proposed changes as query params, simulate both before and after, return the delta.

- [ ] **Step 1: Add DiffOut schema to schemas.py**

```python
class DiffOut(BaseModel):
    role_id: str
    gained: list[SimulatedResource]   # resources newly accessible after change
    lost: list[SimulatedResource]     # resources no longer accessible after change
    unchanged_allowed: int
    unchanged_denied: int
```

- [ ] **Step 2: Write failing test**

```python
# backend/tests/test_diff.py
import pytest


@pytest.fixture
async def rbac(client):
    await client.post("/api/v1/projects", json={"name": "Test"})
    r_admin = await client.post("/api/v1/projects/test/roles", json={"name": "admin"})
    r_perm = await client.post("/api/v1/projects/test/permissions", json={"name": "read_users"})
    r_res = await client.post("/api/v1/projects/test/resources", json={"method": "GET", "path": "/users"})
    perm_id = r_perm.json()["id"]
    res_id = r_res.json()["id"]
    await client.post(f"/api/v1/projects/test/permissions/{perm_id}/resources/{res_id}")
    return {"admin_id": r_admin.json()["id"], "perm_id": perm_id}


async def test_diff_shows_gained_permission(client, rbac):
    """Adding read_users to admin should appear as a gained resource"""
    admin_id = rbac["admin_id"]
    perm_id = rbac["perm_id"]
    r = await client.get(
        f"/api/v1/projects/test/diff/{admin_id}",
        params={"add_permissions": [perm_id]},
    )
    assert r.status_code == 200
    data = r.json()
    assert any(res["path"] == "/users" for res in data["gained"])
    assert data["lost"] == []
```

- [ ] **Step 3: Run test — verify it fails**

```bash
pytest tests/test_diff.py -v
```

Expected: FAIL

- [ ] **Step 4: Add diff endpoint to analyze.py**

```python
from fastapi import Query
from app.schemas import DiffOut, SimulatedResource


@router.get("/projects/{slug}/diff/{role_id}", response_model=DiffOut)
async def diff_role(
    slug: str,
    role_id: str,
    add_permissions: list[str] = Query(default=[]),
    remove_permissions: list[str] = Query(default=[]),
    add_parents: list[str] = Query(default=[]),
    remove_parents: list[str] = Query(default=[]),
    session: AsyncSession = Depends(get_session),
):
    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")

    async def resolve(extra_perm_ids: set[str], excluded_perm_ids: set[str], extra_parent_ids: set[str], excluded_parent_ids: set[str]) -> set[str]:
        """Returns set of allowed resource IDs under given hypothetical state."""
        result = await session.execute(
            text("""
            WITH RECURSIVE role_ancestors AS (
                SELECT :role_id AS id
                UNION ALL
                SELECT ri.parent_role_id
                FROM role_inheritance ri
                JOIN role_ancestors ra ON ri.child_role_id = ra.id
                WHERE ri.parent_role_id NOT IN :excluded_parents
            )
            SELECT DISTINCT rp.permission_id
            FROM role_permissions rp
            WHERE rp.role_id IN (SELECT id FROM role_ancestors)
            AND rp.permission_id NOT IN :excluded_perms
            """),
            {
                "role_id": role_id,
                "excluded_parents": tuple(excluded_parent_ids) or ("",),
                "excluded_perms": tuple(excluded_perm_ids) or ("",),
            },
        )
        perm_ids = {row[0] for row in result.fetchall()} | extra_perm_ids

        if not perm_ids:
            return set()

        res_result = await session.execute(
            text("SELECT resource_id FROM permission_resources WHERE permission_id IN :pids"),
            {"pids": tuple(perm_ids)},
        )
        return {row[0] for row in res_result.fetchall()}

    before_ids = await resolve(set(), set(remove_permissions), set(), set(remove_parents))
    after_ids = await resolve(set(add_permissions), set(remove_permissions), set(add_parents), set(remove_parents))

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
```

- [ ] **Step 5: Run test — verify it passes**

```bash
pytest tests/test_diff.py -v
```

Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/analyze.py backend/app/schemas.py backend/tests/test_diff.py
git commit -m "feat: add policy diff API for what-if role change simulation"
```

---

## Running all tests

```bash
# Backend
cd backend && source venv/bin/activate && pytest tests/ -v

# Frontend
cd frontend && npx vitest run
```
