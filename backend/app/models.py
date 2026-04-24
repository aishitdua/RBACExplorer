import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
