# JobMap — кроссплатформенный сервис поиска работы

> VPS: `104.237.11.110` | Домен: `phone.service247.by` | Статус: MVP

## Возможности

- 🔍 Поиск вакансий: геопространственный (PostGIS), текстовый, по категориям
- 📋 Публикация вакансий: создание, редактирование, геокодирование адреса (Nominatim)
- 📝 Отклики на вакансии: создание, отзыв, принятие/отклонение работодателем
- 🗺️ Карта: MapLibre GL JS + self-hosted тайлы Беларуси (mbtiles)
- 🔐 JWT-аутентификация: регистрация, логин, refresh-токены, загрузка аватаров
- 🚦 Rate limiting (slowapi), Redis-кэширование, health-check с проверкой БД и Redis

## Технологический стек

| Слой          | Технологии                                           |
|---------------|------------------------------------------------------|
| Backend       | Python 3.12, FastAPI, SQLAlchemy (async), Celery     |
| Database      | PostgreSQL 16 + PostGIS 3.4                          |
| Cache         | Redis 7                                             |
| Storage       | MinIO (S3-совместимый)                               |
| Frontend      | TypeScript 5, React 18, Vite, Tailwind CSS, MapLibre |
| Mobile        | Capacitor (iOS / Android)                            |
| Proxy         | Nginx (TLS termination, Let's Encrypt)               |
| Geo           | Nominatim (геокодинг), OSRM (маршруты)               |
| Инфраструктура | Docker Compose, GitHub Actions (CI/CD)              |

## Быстрый старт (локально)

### Требования

- Python 3.12+
- Node.js 18+
- PostgreSQL 16 + PostGIS 3.4
- Redis 7
- Docker и Docker Compose (опционально)

### 1. Клонирование

```bash
git clone <repo-url> jobmap
cd jobmap
```

### 2. Backend

```bash
cd backend
cp .env.example .env          # создай и заполни .env (см. пример ниже)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Swagger: http://localhost:8001/docs
ReDoc: http://localhost:8001/redoc

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                   # Vite dev-server на порту 5173
```

### 4. .env.example (backend)

```env
SERVICE_NAME=JobMap
APP_ENV=development

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=job_service
POSTGRES_USER=job_service
POSTGRES_PASSWORD=<your-password>

REDIS_URL=redis://localhost:6379/0

JWT_SECRET=<generate-with-openssl-rand-hex-32>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

CORS_ORIGINS=http://localhost:5173,http://localhost:3000

S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=job-service
```

## Команды

### Backend

| Команда                | Описание                        |
|------------------------|---------------------------------|
| `pytest`               | Запуск тестов                   |
| `pytest --cov=app`     | Тесты с покрытием               |
| `alembic upgrade head` | Применить миграции              |
| `alembic revision --autogenerate -m "..."` | Создать миграцию |

### Frontend

| Команда           | Описание                       |
|-------------------|--------------------------------|
| `npm run dev`     | Vite dev-сервер                |
| `npm run build`   | Production-сборка              |
| `npm run test`    | Vitest (unit + компонентные)   |
| `npm run lint`    | TypeScript-проверка            |

### Docker

```bash
# Запуск всех сервисов (backend, frontend, nginx, redis, worker, minio)
docker compose up -d

# Просмотр логов
docker compose logs -f backend

# Перезапуск конкретного сервиса
docker compose restart backend
```

## Развёртывание (VPS)

Продакшн развёрнут на VPS `104.237.11.110` (домен `phone.service247.by`).

Детальные инструкции:
- [Реквизиты доступа VPS](docs/Развертывание/Реквизиты_доступа_VPS.md)
- [VPS 104.237.11.110](docs/Развертывание/VPS%20104.237.11.110.md)
- [CI/CD](docs/Развертывание/CI_CD.md)

Краткий порядок деплоя:

```bash
# 1. Залить изменения на VPS
git push origin main

# 2. На VPS (через SSH):
cd /opt/jobmap
git pull
docker compose up -d --build backend worker
docker compose restart backend
```

## Архитектура

Подробная схема компонентов и взаимодействия: [MAP_ARCHITECTURE.md](docs/Архитектура/MAP_ARCHITECTURE.md)

Краткая схема:

```
Браузер / Мобильное приложение
         │
    ┌────▼────┐
    │  Nginx  │ (TLS termination, reverse proxy)
    └────┬────┘
         │
    ┌────┼────────────┬──────────────┐
    ▼    ▼            ▼              ▼
 Frontend  Backend  Tileserver    Nominatim/OSRM
 (static)  :8001    :8080         (geo services)
              │
         ┌────┼────┐
         ▼    ▼    ▼
    PostgreSQL  Redis  MinIO
    + PostGIS
```

## API

- **Swagger UI**: https://phone.service247.by/api/docs
- **ReDoc**: https://phone.service247.by/api/redoc
- **OpenAPI JSON**: https://phone.service247.by/api/openapi.json

### Основные группы эндпоинтов

| Группа        | Префикс                  | Описание                      |
|---------------|--------------------------|-------------------------------|
| auth          | `/api/auth`              | Регистрация, логин, профиль   |
| vacancies     | `/api/vacancies`         | CRUD + геопоиск вакансий      |
| applications  | `/api/applications`      | Отклики на вакансии           |
| geoservices   | `/api/geo`               | Геокодинг, маршруты           |
| health        | `/health`                | Проверка БД и Redis           |

## Структура репозитория

```
├── backend/
│   ├── app/
│   │   ├── routers/         # API-роутеры
│   │   ├── services/        # Бизнес-логика
│   │   ├── models.py        # SQLAlchemy-модели
│   │   ├── schemas.py       # Pydantic-схемы
│   │   └── main.py          # Точка входа
│   ├── tests/               # Тесты (pytest)
│   ├── migrations/          # Alembic-миграции
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React-компоненты
│   │   ├── pages/           # Страницы
│   │   └── stores/          # Zustand-сторы
│   └── package.json
├── deploy/
│   └── nginx/               # Конфигурация Nginx
├── docs/
│   ├── Архитектура/         # MAP_ARCHITECTURE.md и др.
│   └── Развертывание/       # Инструкции по деплою
├── docker-compose.yml       # Docker Compose (все сервисы)
└── README.md
```

## Тестирование

```bash
# Backend
cd backend
pytest                          # все тесты
pytest tests/test_auth.py       # конкретный файл
pytest -k "test_login"          # по названию
pytest --cov=app --cov-report=html  # покрытие

# Frontend
cd frontend
npm run test                    # Vitest run
npm run test:watch             # watch-режим
```

## Лицензия

MIT
