# AGENTS.md — HR-Project (JobMap)

## Проект

Кроссплатформенный сервис поиска работы и подработки.
- Backend: **FastAPI + SQLAlchemy + PostgreSQL + PostGIS + Redis + Celery + MinIO**
- Frontend: **React 18 + TypeScript 5 + Vite 5 + Capacitor 6 + PWA + MapLibre 4**
- Инфраструктура: **Docker Compose на VPS 104.237.11.110**
- Репозиторий Git: `D:\Obsidian\HR` — ветка `infra/initial-audit`
- Класс проекта: **L (Large-scale)**

## Команда профилей (11 профилей)

| # | Профиль | Модель | Специализация |
|---|---------|--------|---------------|
| 1 | `hr-orchestrator` | deepseek-pro | Оркестрация, маршрутизация задач |
| 2 | `hr-change-manager` | deepseek-pro | Классификация запросов, приоритизация |
| 3 | `hr-product-analyst` | deepseek-pro | Формализация требований, user stories |
| 4 | `hr-architect` | deepseek-pro | Архитектура, ADR, тех. решения |
| 5 | `hr-backend-programmer` | deepseek-pro | Backend: FastAPI, PostgreSQL, API |
| 6 | `hr-frontend-programmer` | MiniMax-M3 | Frontend: React, Capacitor, MapLibre |
| 7 | `hr-integration-devops` | deepseek-pro | CI/CD, Docker, VPS, деплой |
| 8 | `hr-code-reviewer` | MiniMax-M3 | Код-ревью, архитектура |
| 9 | `hr-qa-engineer` | deepseek-v4-flash | Тестирование unit/integration/E2E |
| 10 | `hr-security-reviewer` | deepseek-pro | Аудит безопасности |
| 11 | `hr-documenter` | deepseek-pro | Документация, Obsidian |

## Архитектура

- **Backend:** FastAPI, асинхронный (`asyncpg`), Port 8001
- **БД:** PostgreSQL 16 + PostGIS 3.4, Alembic миграции
- **Гео:** Nominatim (geocoding), OSRM (маршруты) — внутренние сервисы (192.168.1.179)
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
- Формат: `feat: описание`, `fix: описание`, `refactor: описание`, `docs: описание`, `test: описание`, `infra: описание`
- Не использовать `--force`, `--amend`, `rebase` без разрешения
- Новые функции в ветках `feature/<name>`, исправления в `fix/<name>`
- Защищённая ветка: `main`
- Worktree обязателен для каждого профиля

### Obsidian:
- Актуальная документация в `D:\Obsidian\HR\`
- Структура:
  - `00_Паспорт проекта.md`
  - `01_Архитектура/`
  - `02_Требования/`
  - `03_Задачи/`
  - `04_ADR/`
  - `05_Развертывание/`
  - `06_Журнал изменений/`
  - `07_Интеграции/`
  - `08_Тестирование/`
  - `09_Проверки Review/`
  - `10_Известные проблемы/`
  - `11_Релизы/`
  - `12_Аудиты/`
- После каждого изменения обновлять `06_Журнал изменений/`
- Архитектурные решения — ADR в `04_ADR/`
- Проверки — `09_Проверки Review/`

### Kanban:
- Доска: `hr-project`
- Статусы (21):
  1. BACKLOG
  2. DISCOVERY
  3. READY_FOR_ANALYSIS
  4. ANALYSIS
  5. READY_FOR_ARCHITECTURE
  6. ARCHITECTURE
  7. READY_FOR_DEVELOPMENT
  8. DEVELOPMENT
  9. READY_FOR_REVIEW
  10. REVIEW
  11. CHANGES_REQUIRED
  12. READY_FOR_QA
  13. QA
  14. READY_FOR_DOCUMENTATION
  15. DOCUMENTATION
  16. READY_FOR_INTEGRATION
  17. INTEGRATION
  18. READY_FOR_USER_ACCEPTANCE
  19. DONE
  20. BLOCKED
  21. CANCELLED

- Orchestrator создаёт задачи с assignee на профиль
- Воркер вызывает `kanban_show()`, работает, `kanban_complete(summary, metadata)`
- Review — отдельная задача на `hr-code-reviewer`
- QA — отдельная задача на `hr-qa-engineer`
- Documentation — отдельная задача на `hr-documenter`

## Workflow (Definition of Done)

Задача считается выполненной, когда:
1. ✅ Требования формализованы (hr-product-analyst)
2. ✅ Архитектурные решения согласованы (hr-architect)
3. ✅ Код реализован (hr-backend-programmer или hr-frontend-programmer)
4. ✅ Выполнен commit по правилам проекта
5. ✅ Тесты написаны и пройдены (hr-qa-engineer)
6. ✅ Code review дал APPROVED (hr-code-reviewer)
7. ✅ Security review выполнен (hr-security-reviewer, если требуется)
8. ✅ Документация обновлена (hr-documenter)
9. ✅ Obsidian обновлён
10. ✅ Известные ограничения записаны
11. ✅ План отката записан (если требуется)
12. ✅ Интеграция завершена (hr-integration-devops)
13. ✅ Оркестратор сформировал итоговый отчёт (hr-orchestrator)

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

Frontend локально:
```bash
cd frontend
npm install
npm run dev
```

Миграции:
```bash
cd backend
alembic upgrade head
```

Тесты:
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## Важные пути
- `D:\Obsidian\HR\` — корень проекта (Git + Obsidian)
- `backend/app/` — Python-код FastAPI
- `backend/migrations/` — Alembic
- `backend/app/main.py` — точка входа
- `backend/app/models.py` — SQLAlchemy модели (15+ таблиц)
- `backend/app/schemas.py` — Pydantic схемы
- `frontend/src/` — React/TypeScript код
- `deploy/` — Docker Compose, Nginx, скрипты
- `.hermes-project/` — проектные политики

## Проектные политики

Все политики находятся в `.hermes-project/`:
- `project.yaml` — конфигурация проекта
- `team.yaml` — конфигурация команды
- `permissions.yaml` — права и ограничения
- `lifecycle.yaml` — жизненный цикл задач
- `bootstrap-report.md` — отчёт развёртывания

## SOUL.md

Каждый профиль имеет собственный SOUL.md:
- `C:\Users\user\AppData\Local\hermes\profiles\<profile-name>\SOUL.md`

SOUL.md содержит:
- Роль и назначение
- Область ответственности
- Обязательный порядок работы
- Правила Git, Kanban, Obsidian
- Запрещённые действия
- Условия блокировки
- Критерии завершения работы

## Безопасность

- Секреты не хранить в Obsidian
- .env не коммитить
- SSH ключи только в `deploy/ssh/`
- Production-deploy только с подтверждения пользователя
- Backup перед каждым развёртыванием

## VPS и инфраструктура

- **VPS:** 104.237.11.110 (Ubuntu 24.04)
- **Гео-сервер:** 192.168.1.179 (Nominatim + OSRM)
- **Docker:** 29.6.2, Docker Compose 5.3.1
- **PostgreSQL:** 16 + PostGIS 3.4
- **Redis:** 7
- **MinIO:** latest

## Контакт для эскалации

Все блокировки и критические вопросы эскалируются через `hr-orchestrator` пользователю.

## Куда жаловаться по ролям

| Проблема | Кому жаловаться | Профиль |
|----------|-----------------|---------|
| Зависла задача, не тот assignee, конфликт приоритетов | Оркестратор | `hr-orchestrator` |
| Размытые требования, неясные критерии приёмки | Продуктовый аналитик | `hr-product-analyst` |
| Архитектурный конфликт, нестыковка компонентов | Архитектор | `hr-architect` |
| Backend-баг, API-ошибка, миграции | Backend-программист | `hr-backend-programmer` |
| Frontend-баг, вёрстка, PWA, карта | Frontend-программист | `hr-frontend-programmer` |
| VPS, Docker, деплой, CI/CD, SSH | DevOps-инженер | `hr-integration-devops` |
| Код не прошёл ревью, спорное решение | Код-ревьюер | `hr-code-reviewer` |
| Тесты падают, низкое покрытие, баги в тестах | QA-инженер | `hr-qa-engineer` |
| Уязвимость, утечка секретов, insecure-конфиг | Security-ревьюер | `hr-security-reviewer` |
| Документация устарела, битые ссылки в Obsidian | Документатор | `hr-documenter` |
| Нужна приоритизация, классификация запроса | Change-менеджер | `hr-change-manager` |

**Правило:** если не знаешь кому → `hr-orchestrator`. Если оркестратор не отвечает → пользователю напрямую.

---

**Дата обновления:** 2026-07-25  
**Класс проекта:** L  
**Количество профилей:** 11  
**Статус:** READY_WITH_LIMITATIONS
