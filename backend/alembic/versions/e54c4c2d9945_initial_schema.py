"""initial schema

Revision ID: e54c4c2d9945
Revises:
Create Date: 2026-04-24 17:42:06.000714

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e54c4c2d9945'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('slug', sa.String(128), unique=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        'roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('project_id', 'name'),
    )
    op.create_table(
        'role_inheritance',
        sa.Column('parent_role_id', sa.String(36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True, index=True),
        sa.Column('child_role_id', sa.String(36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True, index=True),
    )
    op.create_table(
        'permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.UniqueConstraint('project_id', 'name'),
    )
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.String(36), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True, index=True),
        sa.Column('permission_id', sa.String(36), sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True, index=True),
    )
    op.create_table(
        'resources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.UniqueConstraint('project_id', 'method', 'path'),
    )
    op.create_table(
        'permission_resources',
        sa.Column('permission_id', sa.String(36), sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True, index=True),
        sa.Column('resource_id', sa.String(36), sa.ForeignKey('resources.id', ondelete='CASCADE'), primary_key=True, index=True),
    )


def downgrade() -> None:
    op.drop_table('permission_resources')
    op.drop_table('resources')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('role_inheritance')
    op.drop_table('roles')
    op.drop_table('projects')
