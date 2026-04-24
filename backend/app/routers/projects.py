from fastapi import APIRouter, Depends, HTTPException
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Project
from app.schemas import CleanConfirm, ProjectCreate, ProjectOut

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate, session: AsyncSession = Depends(get_session)
):
    slug = body.slug or slugify(body.name)
    existing = await session.scalar(select(Project).where(Project.slug == slug))
    if existing:
        raise HTTPException(400, "Slug already taken")
    project = Project(slug=slug, name=body.name, description=body.description)
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


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


@router.post("/projects/{slug}/clean", status_code=204)
async def clean_project(
    slug: str,
    body: CleanConfirm,
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import delete

    from app.models import Permission, Resource, Role

    if body.confirm != slug:
        raise HTTPException(400, "Confirmation slug does not match")

    project = await session.scalar(select(Project).where(Project.slug == slug))
    if not project:
        raise HTTPException(404, "Project not found")

    # Delete all children
    await session.execute(delete(Role).where(Role.project_id == project.id))
    await session.execute(delete(Permission).where(Permission.project_id == project.id))
    await session.execute(delete(Resource).where(Resource.project_id == project.id))

    await session.commit()
