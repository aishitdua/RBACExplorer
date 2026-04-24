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
