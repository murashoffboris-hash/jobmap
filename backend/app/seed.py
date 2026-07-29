"""Seed script for development / test environment.

Usage:
    python -m app.seed                 # full seed (categories, users, vacancies)
    python -m app.seed --dev           # same as above (preserved for compatibility)
    python -m app.seed --categories    # seed only categories
    python -m app.seed --users         # seed only test users
    python -m app.seed --vacancies     # seed only vacancies

Creates:
  - 20 categories (Строительство, IT, Транспорт, Продажи, Медицина, ...)
  - 3 test users (employer, worker, admin) with password "password123"
  - ~60 vacancies across 6 categories in Minsk area
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings

# ── Constants ──────────────────────────────────────────────────────

CATEGORIES = [
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

TEST_USERS = [
    {"email": "employer@test.by", "password": "password123", "role": "employer", "name": "Иван Петров"},
    {"email": "worker@test.by", "password": "password123", "role": "user", "name": "Мария Сидорова"},
    {"email": "admin@test.by", "password": "password123", "role": "admin", "name": "Администратор"},
]

# Minsk center coordinates
MINSK_LAT = 53.9
MINSK_LNG = 27.5

VACANCY_TITLES_BY_CATEGORY = {
    "stroitelstvo": [
        "Разнорабочий на стройку",
        "Каменщик",
        "Маляр-штукатур",
        "Электромонтажник",
        "Сварщик",
        "Прораб",
        "Кровельщик",
        "Отделочник",
        "Бетонщик",
        "Разнорабочий (подсобный)",
    ],
    "it-telecom": [
        "Python-разработчик",
        "Frontend-разработчик (React)",
        "UX/UI дизайнер",
        "Системный администратор",
        "Тестировщик (QA)",
        "DevOps инженер",
        "Менеджер проектов",
        "Java-разработчик",
        "Аналитик данных",
        "Техническая поддержка",
    ],
    "transport": [
        "Курьер (пеший)",
        "Курьер на авто",
        "Водитель-экспедитор",
        "Кладовщик",
        "Сортировщик",
        "Оператор колл-центра",
        "Комплектовщик заказов",
        "Водитель (категория B)",
        "Грузчик",
        "Менеджер по логистике",
    ],
    "cleaning": [
        "Уборщица / уборщик",
        "Клинер офисных помещений",
        "Мойщик окон",
        "Уборщик территории",
        "Химчистка / прачечная",
    ],
    "sales": [
        "Продавец-консультант",
        "Кассир",
        "Торговый представитель",
        "Менеджер по продажам",
        "Продавец на рынке",
        "Оператор торгового зала",
        "Мерчендайзер",
        "Специалист по продажам B2B",
        "Ассистент отдела продаж",
        "Продавец непродовольственных товаров",
    ],
    "horeca": [
        "Официант",
        "Бармен",
        "Повар",
        "Администратор ресторана",
        "Хостес",
        "Мойщик посуды",
        "Горничная",
        "Администратор гостиницы",
        "Портье",
        "Помощник повара",
    ],
}

PASSWORD_HASH_CACHE: dict[str, str] = {}


# ── Helpers ────────────────────────────────────────────────────────

def _get_or_create_engine():
    """Create a sync engine from the settings."""
    return create_engine(
        settings.sync_database_url,
        echo=settings.APP_ENV == "development",
        pool_pre_ping=True,
    )


def _get_hashed_password(plain: str) -> str:
    """Return a cached bcrypt hash (generated once)."""
    if plain not in PASSWORD_HASH_CACHE:
        from passlib.context import CryptContext

        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        PASSWORD_HASH_CACHE[plain] = ctx.hash(plain)
    return PASSWORD_HASH_CACHE[plain]


def _random_offset() -> tuple[float, float]:
    """Return a random lat/lng offset ~0.5km around Minsk center."""
    import random
    # ~0.0045 deg ≈ 500m at 54°N
    lat = MINSK_LAT + random.uniform(-0.02, 0.02)
    lng = MINSK_LNG + random.uniform(-0.02, 0.02)
    return round(lat, 6), round(lng, 6)


# ── Seed functions ────────────────────────────────────────────────

def seed_categories(session: Session) -> dict[str, int]:
    """Insert categories, return {slug: id} mapping."""
    result = {}
    for cat in CATEGORIES:
        row = session.execute(
            text("SELECT id FROM categories WHERE slug = :slug"),
            {"slug": cat["slug"]},
        ).fetchone()
        if row:
            result[cat["slug"]] = row[0]
            print(f"  Category '{cat['name']}' already exists (id={row[0]})")
        else:
            r = session.execute(
                text(
                    "INSERT INTO categories (name, slug, icon, is_active, created_at, updated_at) "
                    "VALUES (:name, :slug, :icon, true, now(), now()) "
                    "RETURNING id"
                ),
                cat,
            ).fetchone()
            result[cat["slug"]] = r[0]
            print(f"  ✓ Created category '{cat['name']}' (id={r[0]})")
    session.commit()
    return result


def seed_users(session: Session) -> dict[str, int]:
    """Insert test users, return {email: id} mapping."""
    result = {}
    for u in TEST_USERS:
        row = session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": u["email"]},
        ).fetchone()
        if row:
            result[u["email"]] = row[0]
            print(f"  User '{u['email']}' already exists (id={row[0]})")
        else:
            hashed = _get_hashed_password(u["password"])
            r = session.execute(
                text(
                    "INSERT INTO users (email, hashed_password, role, is_active, email_verified, created_at, updated_at) "
                    "VALUES (:email, :hashed, :role, true, true, now(), now()) "
                    "RETURNING id"
                ),
                {"email": u["email"], "hashed": hashed, "role": u["role"]},
            ).fetchone()
            user_id = r[0]
            # Create profile
            session.execute(
                text(
                    "INSERT INTO profiles (user_id, full_name, created_at, updated_at) "
                    "VALUES (:uid, :name, now(), now()) "
                    "ON CONFLICT (user_id) DO NOTHING"
                ),
                {"uid": user_id, "name": u["name"]},
            )
            result[u["email"]] = user_id
            print(f"  ✓ Created user '{u['email']}' (id={user_id}, role={u['role']})")
    session.commit()
    return result


def seed_vacancies(session: Session, category_map: dict[str, int], user_map: dict[str, int]):
    """Insert sample vacancies in Minsk for each category."""
    employer_id = user_map.get("employer@test.by")
    if employer_id is None:
        print("  ⚠ Employer user not found — skipping vacancies")
        return

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=30)

    for cat_slug, titles in VACANCY_TITLES_BY_CATEGORY.items():
        cat_id = category_map.get(cat_slug)
        if cat_id is None:
            print(f"  ⚠ Category '{cat_slug}' not found — skipping")
            continue

        for i, title in enumerate(titles):
            lat, lng = _random_offset()
            # Check if vacancy already exists
            slug = f"{title}-{cat_slug}-seed"
            _hash_val = sha256(slug.encode()).hexdigest()[:12]
            existing = session.execute(
                text("SELECT id FROM vacancies WHERE title = :title AND category_id = :cat_id AND owner_id = :owner"),
                {"title": title, "cat_id": cat_id, "owner": employer_id},
            ).fetchone()
            if existing:
                print(f"  Vacancy '{title}' already exists (id={existing[0]})")
                continue

            session.execute(
                text("""
                    INSERT INTO vacancies (
                        owner_id, category_id, title, description,
                        location, location_lat, location_lon,
                        address_raw, salary_from, salary_to, salary_currency,
                        schedule_type, status, expires_at,
                        contact_name, created_at, updated_at
                    ) VALUES (
                        :owner_id, :category_id, :title, :description,
                        ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
                        :lat, :lng, :address, :salary_from, :salary_to, 'BYN',
                        :schedule, 'active', :expires,
                        'test-company', now(), now()
                    )
                """),
                {
                    "owner_id": employer_id,
                    "category_id": cat_id,
                    "title": title,
                    "description": f"Тестовая вакансия: {title}. Отличные условия работы, дружный коллектив.",
                    "lat": lat,
                    "lng": lng,
                    "address": f"г. Минск, {['ул. Ленина', 'пр. Независимости', 'ул. Пушкина', 'ул. Гагарина', 'ул. Коласа'][i % 5]}, д. {10 + i}",
                    "salary_from": 800 + i * 100,
                    "salary_to": 1500 + i * 150,
                    "schedule": "full-time",
                    "expires": expires,
                },
            )
            print(f"  ✓ Created vacancy {i+1}/{len(titles)}: '{title}' in '{cat_slug}'")

    session.commit()
    print(f"  All vacancies created under employer (id={employer_id})")


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed the JobMap database with test data")
    parser.add_argument("--dev", action="store_true", help="Alias for full seed")
    parser.add_argument("--categories", action="store_true", help="Seed only categories")
    parser.add_argument("--users", action="store_true", help="Seed only test users")
    parser.add_argument("--vacancies", action="store_true", help="Seed only vacancies")
    args = parser.parse_args()

    full = args.dev or not (args.categories or args.users or args.vacancies)

    engine = _get_or_create_engine()

    with engine.begin() as conn:
        # Ensure ENUM types exist (created by migration, but safe guard)
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE userrole AS ENUM ('user', 'employer', 'admin', 'moderator');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE vacancystatus AS ENUM ('draft', 'pending', 'active', 'filled', 'expired', 'archived');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE responsestatus AS ENUM ('pending', 'accepted', 'rejected', 'cancelled');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE notificationtype AS ENUM ('new_response', 'response_status', 'new_message', 'vacancy_expired', 'system');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """))

    with Session(engine) as session:
        print("🌱 Seeding JobMap database…")
        print()

        category_map = {}
        user_map = {}

        if full or args.categories:
            print("📁 Categories:")
            category_map = seed_categories(session)
            print()

        if full or args.users:
            print("👤 Users:")
            user_map = seed_users(session)
            print()

        if full or args.vacancies:
            if not category_map and full:
                # Reload category map from DB if not freshly seeded
                rows = session.execute(text("SELECT slug, id FROM categories")).fetchall()
                category_map = {r[0]: r[1] for r in rows}
            print("💼 Vacancies:")
            seed_vacancies(session, category_map, user_map)
            print()

        print("✅ Seeding complete!")


if __name__ == "__main__":
    main()
