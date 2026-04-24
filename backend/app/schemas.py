from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    slug: str | None = None


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
    name: str | None = None
    description: str | None = None
    color: str | None = None


class RoleOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    color: str
    parents: list[str] = []
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    name: str
    description: str = ""


class PermissionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


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
    method: str | None = None
    path: str | None = None
    description: str | None = None


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
    granted_by_permission: str | None = None
    granted_by_role: str | None = None


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


class DiffOut(BaseModel):
    role_id: str
    gained: list[SimulatedResource]  # resources newly accessible after change
    lost: list[SimulatedResource]  # resources no longer accessible after change
    unchanged_allowed: int
    unchanged_denied: int
