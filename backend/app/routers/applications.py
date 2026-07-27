"""Applications API — FR-007: отклики на вакансии."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_session
from app.models import Application, ApplicationStatus, User, Vacancy, VacancyStatus
from app.schemas import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/applications", tags=["applications"])

# Vacancy-scoped routes are on a separate router with a shared prefix-like path
vacancy_applications_router = APIRouter(tags=["vacancy-applications"])


def _sanitize_html(text: str | None) -> str | None:
    """Strip all HTML tags, leaving plain text only (EC-8)."""
    if text is None:
        return None
    return re.sub(r"<[^>]*>", "", text)


def _application_to_response(app: Application) -> ApplicationResponse:
    """Build response with eagerly loaded relationship data."""
    return ApplicationResponse(
        id=app.id,
        user_id=app.user_id,
        vacancy_id=app.vacancy_id,
        cover_letter=app.cover_letter,
        status=app.status.value,
        vacancy_title=app.vacancy.title if app.vacancy else None,
        employer_name=(
            app.vacancy.owner.profile.full_name
            if app.vacancy and app.vacancy.owner and app.vacancy.owner.profile
            else None
        ),
        applicant_name=(
            app.user.profile.full_name
            if app.user and app.user.profile
            else None
        ),
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


# ── Соискатель: создать отклик ──────────────────────────────────

@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(
    data: ApplicationCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Создать отклик на вакансию (C1-C4, C8)."""
    # C3: vacancy must exist and not be soft-deleted (archived)
    vacancy = await session.get(Vacancy, data.vacancy_id)
    if not vacancy or vacancy.status == VacancyStatus.ARCHIVED:
        raise HTTPException(status_code=404, detail="Вакансия недоступна")

    # C2: cannot apply to own vacancy
    if vacancy.owner_id == current_user.id:
        raise HTTPException(
            status_code=403, detail="Нельзя откликнуться на свою вакансию"
        )

    # C1: duplicate check
    existing = await session.execute(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.vacancy_id == data.vacancy_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Вы уже откликнулись на эту вакансию"
        )

    # EC-8: sanitize cover_letter
    clean_letter = _sanitize_html(data.cover_letter)

    app = Application(
        user_id=current_user.id,
        vacancy_id=data.vacancy_id,
        cover_letter=clean_letter,
        status=ApplicationStatus.PENDING,
    )
    session.add(app)
    await session.commit()

    # Reload with relationships
    result = await session.execute(
        select(Application)
        .options(
            selectinload(Application.user).selectinload(User.profile),
            selectinload(Application.vacancy)
            .selectinload(Vacancy.owner)
            .selectinload(User.profile),
        )
        .where(Application.id == app.id)
    )
    app = result.scalar_one()
    return _application_to_response(app)


# ── Соискатель: мои отклики (paginated) ─────────────────────────

@router.get("", response_model=ApplicationListResponse)
async def list_my_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Список моих откликов — сортировка created_at DESC (FR-007.2)."""
    base = (
        select(Application)
        .options(
            selectinload(Application.user).selectinload(User.profile),
            selectinload(Application.vacancy)
            .selectinload(Vacancy.owner)
            .selectinload(User.profile),
        )
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
    )

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    result = await session.execute(base.offset(offset).limit(page_size))
    items = [_application_to_response(a) for a in result.scalars().all()]

    return ApplicationListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


# ── Соискатель: отозвать отклик ─────────────────────────────────

@router.patch("/{application_id}/withdraw", response_model=ApplicationResponse)
async def withdraw_application(
    application_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Отозвать свой pending-отклик (C5)."""
    app = await session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Отклик не найден")

    if app.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы не автор этого отклика")

    # C5: only pending can be withdrawn
    if app.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail="Можно отозвать только отклик в статусе 'pending'",
        )

    app.status = ApplicationStatus.WITHDRAWN
    await session.commit()

    # Reload with relationships
    result = await session.execute(
        select(Application)
        .options(
            selectinload(Application.user).selectinload(User.profile),
            selectinload(Application.vacancy)
            .selectinload(Vacancy.owner)
            .selectinload(User.profile),
        )
        .where(Application.id == app.id)
    )
    return _application_to_response(result.scalar_one())


# ── Работодатель: изменить статус отклика (accept/reject) ──────

async def _change_application_status(
    application_id: int,
    new_status: ApplicationStatus,
    session: AsyncSession,
    current_user: User,
) -> Application:
    """Shared helper: validate ownership + pending state, then change status.

    Raises HTTPException on any violation (C6, C7).
    Returns the updated Application (not yet committed — caller must commit).
    """
    app = await session.get(
        Application,
        application_id,
        options=[selectinload(Application.vacancy)],
    )
    if not app:
        raise HTTPException(status_code=404, detail="Отклик не найден")

    # C6: only vacancy owner can change status
    if not app.vacancy or app.vacancy.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Только владелец вакансии может изменять статус отклика",
        )

    # C7: only pending applications can transition
    if app.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=409,
            detail=f"Нельзя изменить статус: отклик уже находится в состоянии '{app.status.value}'",
        )

    app.status = new_status
    return app


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def update_application_status(
    application_id: int,
    data: ApplicationStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Принять или отклонить отклик — только владелец вакансии (C6, C7)."""
    new_status = ApplicationStatus(data.status)

    app = await _change_application_status(
        application_id, new_status, session, current_user
    )
    await session.commit()

    # Reload with all relationships for the response
    result = await session.execute(
        select(Application)
        .options(
            selectinload(Application.user).selectinload(User.profile),
            selectinload(Application.vacancy)
            .selectinload(Vacancy.owner)
            .selectinload(User.profile),
        )
        .where(Application.id == app.id)
    )
    return _application_to_response(result.scalar_one())


# ── Работодатель: отклики на мою вакансию ───────────────────────

@vacancy_applications_router.get(
    "/api/vacancies/{vacancy_id}/applications",
    response_model=ApplicationListResponse,
)
async def list_vacancy_applications(
    vacancy_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Список откликов на вакансию — только для владельца (FR-007.4)."""
    vacancy = await session.get(Vacancy, vacancy_id)
    if not vacancy:
        raise HTTPException(status_code=404, detail="Вакансия не найдена")

    if vacancy.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    base = (
        select(Application)
        .options(
            selectinload(Application.user).selectinload(User.profile),
            selectinload(Application.vacancy)
            .selectinload(Vacancy.owner)
            .selectinload(User.profile),
        )
        .where(Application.vacancy_id == vacancy_id)
        .order_by(Application.created_at.desc())
    )

    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar_one()

    offset = (page - 1) * page_size
    result = await session.execute(base.offset(offset).limit(page_size))
    items = [_application_to_response(a) for a in result.scalars().all()]

    return ApplicationListResponse(
        items=items, total=total, page=page, page_size=page_size
    )
