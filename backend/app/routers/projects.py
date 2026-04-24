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
