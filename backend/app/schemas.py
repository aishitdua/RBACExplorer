from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1024)
    slug: str | None = Field(default=None, max_length=128, pattern=r"^[a-z0-9-]+$")


class ProjectOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1024)
    color: str = Field(default="#60a5fa", pattern=r"^#[0-9a-fA-F]{6}$")


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


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
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=1024)


class PermissionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=1024)


class PermissionOut(BaseModel):
    id: str
    project_id: str
    name: str
    description: str

    model_config = {"from_attributes": True}


class ResourceCreate(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = Field(
        max_length=512,
        pattern=r"^/[a-zA-Z0-9/_{}.\-]*$",
    )
    description: str = Field(default="", max_length=1024)


class ResourceUpdate(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] | None = None
    path: str | None = Field(
        default=None,
        max_length=512,
        pattern=r"^/[a-zA-Z0-9/_{}.\-]*$",
    )
    description: str | None = Field(default=None, max_length=1024)


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


class CleanConfirm(BaseModel):
    confirm: str
