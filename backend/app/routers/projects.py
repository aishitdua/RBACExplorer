import logging

from fastapi import APIRouter, HTTPException
from slugify import slugify
from sqlalchemy import delete, select

from app.dependencies import CurrentUser, DBSession, get_project_for_user_or_404
from app.models import Permission, Project, Resource, Role
from app.schemas import CleanConfirm, ProjectCreate, ProjectOut

logger = logging.getLogger(__name__)

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    session: DBSession,
    current_user: CurrentUser,
):
    slug = body.slug or slugify(body.name)
    existing = await session.scalar(
        select(Project).where(
            Project.slug == slug, Project.owner_user_id == current_user
        )
    )
    if existing:
        raise HTTPException(400, "Slug already taken")
    project = Project(
        slug=slug,
        name=body.name,
        description=body.description,
        owner_user_id=current_user,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    logger.info("project.created slug=%s name=%s", project.slug, project.name)
    return project


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(
    session: DBSession,
    current_user: CurrentUser,
):
    result = await session.execute(
        select(Project)
        .where(Project.owner_user_id == current_user)
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get("/projects/{slug}", response_model=ProjectOut)
async def get_project(
    slug: str,
    session: DBSession,
    current_user: CurrentUser,
):
    return await get_project_for_user_or_404(slug, current_user, session)


@router.delete("/projects/{slug}", status_code=204)
async def delete_project(
    slug: str,
    session: DBSession,
    current_user: CurrentUser,
):
    project = await get_project_for_user_or_404(slug, current_user, session)
    await session.delete(project)
    await session.commit()
    logger.info("project.deleted slug=%s", slug)


@router.post("/projects/{slug}/clean", status_code=204)
async def clean_project(
    slug: str,
    body: CleanConfirm,
    session: DBSession,
    current_user: CurrentUser,
):
    if body.confirm != slug:
        raise HTTPException(400, "Confirmation slug does not match")

    project = await get_project_for_user_or_404(slug, current_user, session)

    # Delete all children
    await session.execute(delete(Role).where(Role.project_id == project.id))
    await session.execute(delete(Permission).where(Permission.project_id == project.id))
    await session.execute(delete(Resource).where(Resource.project_id == project.id))

    await session.commit()
    logger.warning("project.cleaned slug=%s", slug)
