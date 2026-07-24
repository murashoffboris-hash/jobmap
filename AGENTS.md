# AGENTS.md — HR-Project (JobMap)

## Проект

Кроссплатформенный сервис поиска работы и подработки.
- Backend: **FastAPI + SQLAlchemy + PostgreSQL + PostGIS + Redis + Celery + MinIO**
- Frontend: **React 18 + TypeScript 5 + Vite 5 + Capacitor 6 + PWA + MapLibre 4**
- Инфраструктура: **Docker Compose на VPS 104.237.11.110**
- Репозиторий Git: `D:\Obsidian\HR` — ветка `infra/initial-audit`

## Команда профилей

| Профиль | Модель | Специализация |
|---|---|---|
| `orchestrator` | Qwen 3.7 Plus (DashScope) | Оркестрация, декомпозиция планов |
| `programmer-qwen` | Qwen 3.6 Plus (DashScope) | Бэкенд, API, БД, PostGIS, авторизация |
| `programmer` | DeepSeek Flash (OpenRouter) | Общая разработка (средняя сложность) |
| `programmer-minimax` | MiniMax M3 (MiniMax) | Фронтенд, React, Capacitor, MapLibre |
| `tester` | DeepSeek Flash (OpenRouter) | Тестирование (unit, integration, E2E) |
| `reviewer` | MiniMax M3 (MiniMax) | Код-ревью, архитектура, безопасность |

## Архитектура

- **Backend:** FastAPI, асинхронный (`asyncpg`), Port 8001
- **БД:** PostgreSQL 16 + PostGIS 3.4, Alembic миграции
- **Гео:** Nominatim (geocoding), OSRM (маршруты) — внутренние сервисы
- **Кэш/очереди:** Redis 7
- **Файлы:** MinIO (S3-совместимый сторадж)
- **Web-сервер:** Nginx (reverse proxy, HTTPS)

## Правила работы

### Обязательно перед началом:
```bash
git status
git branch --show-current
git log --oneline -10
```

### Git-коммиты:
- Сообщения на **русском языке**
- Формат: `feat: описание`, `fix: описание`, `refactor: описание`
- Не использовать `--force`, `--amend`, `rebase` без разрешения
- Новые функции в ветках `feature/<name>`, исправления в `fix/<name>`

### Obsidian:
- Актуальная документация в `D:\Obsidian\HR\`
- После каждого изменения обновлять `06 Журнал изменений.md`
- Архитектурные решения — ADR в `Решения ADR\`
- Проверки — `09 Проверки Review.md`

### Kanban:
- Работаем на доске `hr-project`
- Orchestrator создаёт задачи с assignee на профиль
- Воркер вызывает `kanban_show()`, работает, `kanban_complete(summary, metadata)`
- Review — отдельная задача на `reviewer`
- Флаг `ROLE=PROGRAMMER` или `ROLE=REVIEWER` для контекста

## Команды для сборки

Backend с Docker:
```bash
docker compose up -d
```

Backend локально:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Миграции:
```bash
cd backend
alembic upgrade head
```

Тесты:
```bash
# pytest, конкретные команды уточнять по проекту
```

## Важные пути
- `D:\Obsidian\HR\` — корень проекта (Git + Obsidian)
- `backend/app/` — Python-код FastAPI
- `backend/migrations/` — Alembic
- `backend/app/main.py` — точка входа
- `backend/app/models.py` — SQLAlchemy модели (15+ таблиц)
- `backend/app/schemas.py` — Pydantic схемы
- `deploy/` — Docker Compose, Nginx, скрипты
