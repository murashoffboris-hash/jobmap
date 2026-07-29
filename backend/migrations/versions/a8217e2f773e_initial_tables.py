"""Initial tables with ENUM types and PostGIS support.

Revision ID: a8217e2f773e
Revises: 
Create Date: 2026-07-23 08:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'a8217e2f773e'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ENUM types were created manually via psql before running this migration
    op.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            role userrole DEFAULT 'user'::userrole NOT NULL,
            is_active BOOLEAN DEFAULT true NOT NULL,
            email_verified BOOLEAN DEFAULT false NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_users_email ON users (email)")

    op.execute("""
        CREATE TABLE profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE UNIQUE,
            full_name VARCHAR(255),
            phone VARCHAR(32),
            avatar_url VARCHAR(512),
            bio TEXT,
            search_lat FLOAT,
            search_lon FLOAT,
            search_radius_km FLOAT DEFAULT 10.0,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(128) NOT NULL UNIQUE,
            slug VARCHAR(128) NOT NULL UNIQUE,
            parent_id INTEGER REFERENCES categories(id),
            icon VARCHAR(64),
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_categories_slug ON categories (slug)")

    op.execute("""
        CREATE TABLE vacancies (
            id SERIAL PRIMARY KEY,
            owner_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            title VARCHAR(255) NOT NULL,
            description TEXT,
            status vacancystatus DEFAULT 'active'::vacancystatus NOT NULL,
            location GEOGRAPHY(POINT, 4326),
            location_lat FLOAT,
            location_lon FLOAT,
            address_raw VARCHAR(512),
            address_normalized VARCHAR(512),
            osm_id VARCHAR(64),
            location_type VARCHAR(64),
            location_accuracy FLOAT,
            salary_from INTEGER,
            salary_to INTEGER,
            salary_currency VARCHAR(8) DEFAULT 'BYN',
            schedule_type VARCHAR(64),
            contact_phone VARCHAR(32),
            contact_name VARCHAR(128),
            exact_location_public BOOLEAN DEFAULT false,
            scheduled_publish_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_vacancies_owner_id ON vacancies (owner_id)")
    op.execute("CREATE INDEX ix_vacancies_status ON vacancies (status)")
    op.execute("CREATE INDEX ix_vacancies_title ON vacancies (title)")
    op.execute("CREATE INDEX ix_vacancies_location_lat_lon ON vacancies (location_lat, location_lon)")
    op.execute("CREATE INDEX idx_vacancies_location ON vacancies USING GIST (location)")

    op.execute("""
        CREATE TABLE vacancy_media (
            id SERIAL PRIMARY KEY,
            vacancy_id INTEGER REFERENCES vacancies(id) ON DELETE CASCADE NOT NULL,
            media_type VARCHAR(16) NOT NULL,
            file_url VARCHAR(512) NOT NULL,
            thumbnail_url VARCHAR(512),
            s3_key VARCHAR(512) NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_vacancy_media_vacancy_id ON vacancy_media (vacancy_id)")

    op.execute("""
        CREATE TABLE responses (
            id SERIAL PRIMARY KEY,
            vacancy_id INTEGER REFERENCES vacancies(id) ON DELETE CASCADE NOT NULL,
            requester_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            status responsestatus DEFAULT 'pending'::responsestatus NOT NULL,
            message TEXT,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            CONSTRAINT uq_response_vacancy_user UNIQUE (vacancy_id, requester_id)
        )
    """)
    op.execute("CREATE INDEX ix_responses_vacancy_id ON responses (vacancy_id)")
    op.execute("CREATE INDEX ix_responses_requester_id ON responses (requester_id)")

    op.execute("""
        CREATE TABLE chats (
            id SERIAL PRIMARY KEY,
            vacancy_id INTEGER REFERENCES vacancies(id) ON DELETE CASCADE,
            user_one_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            user_two_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            is_archived BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE messages (
            id SERIAL PRIMARY KEY,
            chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE NOT NULL,
            sender_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            text TEXT,
            is_read BOOLEAN DEFAULT false,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_messages_chat_id ON messages (chat_id)")

    op.execute("""
        CREATE TABLE work_status_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            vacancy_id INTEGER REFERENCES vacancies(id),
            event_type VARCHAR(64) NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_work_status_events_user_id ON work_status_events (user_id)")

    op.execute("""
        CREATE TABLE reviews (
            id SERIAL PRIMARY KEY,
            reviewer_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            reviewed_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            vacancy_id INTEGER REFERENCES vacancies(id),
            rating INTEGER NOT NULL,
            comment TEXT,
            is_visible BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_reviews_reviewer_id ON reviews (reviewer_id)")
    op.execute("CREATE INDEX ix_reviews_reviewed_user_id ON reviews (reviewed_user_id)")

    op.execute("""
        CREATE TABLE subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            category_id INTEGER REFERENCES categories(id),
            location_lat FLOAT,
            location_lon FLOAT,
            radius_km FLOAT DEFAULT 10.0,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_subscriptions_user_id ON subscriptions (user_id)")

    op.execute("""
        CREATE TABLE promotions (
            id SERIAL PRIMARY KEY,
            vacancy_id INTEGER REFERENCES vacancies(id) ON DELETE CASCADE,
            promo_type VARCHAR(64) NOT NULL,
            starts_at TIMESTAMPTZ NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)

    op.execute("""
        CREATE TABLE notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            notification_type notificationtype NOT NULL,
            title VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            is_read BOOLEAN DEFAULT false,
            payload JSONB,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_notifications_user_id ON notifications (user_id)")

    op.execute("""
        CREATE TABLE geocoding_log (
            id SERIAL PRIMARY KEY,
            address_raw VARCHAR(512) NOT NULL,
            address_normalized VARCHAR(512),
            lat FLOAT,
            lon FLOAT,
            osm_id VARCHAR(64),
            result_type VARCHAR(64),
            accuracy FLOAT,
            raw_response JSONB,
            success BOOLEAN DEFAULT true,
            vacancy_id INTEGER REFERENCES vacancies(id),
            error_message VARCHAR(512),
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            CONSTRAINT uq_geocode_addr_vacancy UNIQUE (address_raw, vacancy_id)
        )
    """)
    op.execute("CREATE INDEX ix_geocoding_log_address_raw ON geocoding_log (address_raw)")

    op.execute("""
        CREATE TABLE audit_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            action VARCHAR(128) NOT NULL,
            target_type VARCHAR(64),
            target_id INTEGER,
            details JSONB,
            ip_address VARCHAR(64),
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS geocoding_log CASCADE")
    op.execute("DROP TABLE IF EXISTS notifications CASCADE")
    op.execute("DROP TABLE IF EXISTS promotions CASCADE")
    op.execute("DROP TABLE IF EXISTS subscriptions CASCADE")
    op.execute("DROP TABLE IF EXISTS reviews CASCADE")
    op.execute("DROP TABLE IF EXISTS work_status_events CASCADE")
    op.execute("DROP TABLE IF EXISTS messages CASCADE")
    op.execute("DROP TABLE IF EXISTS chats CASCADE")
    op.execute("DROP TABLE IF EXISTS responses CASCADE")
    op.execute("DROP TABLE IF EXISTS vacancy_media CASCADE")
    op.execute("DROP TABLE IF EXISTS vacancies CASCADE")
    op.execute("DROP TABLE IF EXISTS categories CASCADE")
    op.execute("DROP TABLE IF EXISTS profiles CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")
