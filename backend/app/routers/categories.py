"""Categories public API — справочник категорий."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models import Category
from app.schemas import CategoryResponse

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get(
    "",
    response_model=list[CategoryResponse],
    summary="Список категорий",
    description="Публичный справочник активных категорий вакансий.",
)
async def list_categories(
    session: AsyncSession = Depends(get_session),
) -> list[CategoryResponse]:
    result = await session.execute(
        select(Category)
        .where(Category.is_active == True)  # noqa: E712
        .order_by(Category.name)
    )
    return [
        CategoryResponse.model_validate(cat)
        for cat in result.scalars().all()
    ]
