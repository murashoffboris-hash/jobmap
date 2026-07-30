"""Seed only categories — standalone script for production/VPS deployment.

Usage:
    python -m app.seed_categories          # insert 20 categories (idempotent)

Designed to be run inside the backend container:
    docker cp backend/app/seed_categories.py jobmap-backend-1:/app/app/
    docker exec jobmap-backend-1 python -m app.seed_categories
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings

# 20+ categories — slug (latin), name (Russian), emoji icon
CATEGORIES: list[dict[str, str]] = [
    {"name": "Строительство / ремонт",       "slug": "stroitelstvo",          "icon": "🏗️"},
    {"name": "Транспорт / логистика",        "slug": "transport",             "icon": "🚛"},
    {"name": "IT / телеком",                 "slug": "it-telecom",            "icon": "💻"},
    {"name": "Продажи / торговля",           "slug": "sales",                 "icon": "🛒"},
    {"name": "Медицина",                     "slug": "medicine",              "icon": "🏥"},
    {"name": "Образование",                  "slug": "education",             "icon": "📚"},
    {"name": "Финансы / бухгалтерия",        "slug": "finance",               "icon": "💰"},
    {"name": "HoReCa (гостиницы / рестораны)", "slug": "horeca",              "icon": "🍽️"},
    {"name": "Охрана / безопасность",        "slug": "security",              "icon": "🛡️"},
    {"name": "Производство",                 "slug": "production",            "icon": "🏭"},
    {"name": "Клининг / уборка",             "slug": "cleaning",              "icon": "🧹"},
    {"name": "Красота / спорт",              "slug": "beauty-sport",          "icon": "💪"},
    {"name": "Юриспруденция",                "slug": "legal",                 "icon": "⚖️"},
    {"name": "Маркетинг / реклама",          "slug": "marketing",             "icon": "📢"},
    {"name": "HR / персонал",                "slug": "hr",                    "icon": "👥"},
    {"name": "Искусство / дизайн",           "slug": "art-design",            "icon": "🎨"},
    {"name": "Сельское хозяйство",           "slug": "agriculture",           "icon": "🌾"},
    {"name": "Госслужба",                    "slug": "government",            "icon": "🏛️"},
    {"name": "Неквалифицированный труд",     "slug": "unskilled-labor",       "icon": "🔧"},
    {"name": "Другое",                       "slug": "other",                 "icon": "📌"},
]


def seed(session: Session) -> int:
    """Insert categories (idempotent — skips existing by slug). Returns count created."""
    created = 0
    for cat in CATEGORIES:
        row = session.execute(
            text("SELECT id FROM categories WHERE slug = :slug"),
            {"slug": cat["slug"]},
        ).fetchone()
        if row:
            print(f"  ⏭ {cat['icon']} {cat['name']} — уже существует (id={row[0]})")
        else:
            r = session.execute(
                text(
                    "INSERT INTO categories (name, slug, icon, is_active, created_at, updated_at) "
                    "VALUES (:name, :slug, :icon, true, now(), now()) "
                    "RETURNING id"
                ),
                cat,
            ).fetchone()
            created += 1
            print(f"  ✅ {cat['icon']} {cat['name']} — создана (id={r[0]})")
    session.commit()
    return created


def main() -> None:
    engine = create_engine(
        settings.sync_database_url,
        pool_pre_ping=True,
    )

    with Session(engine) as session:
        print(f"🌱 Сидирование категорий ({len(CATEGORIES)} шт.)…")
        print()
        n = seed(session)
        print()
        print(f"✅ Готово: {n} новых, {len(CATEGORIES) - n} уже существовали.")


if __name__ == "__main__":
    main()
