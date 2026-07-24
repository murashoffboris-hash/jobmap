# 09 Проверки Review — JobMap

Чеклист для code review и архитектурных проверок.

## Backend
- [x] FastAPI async (`asyncpg`), порт 8001
- [x] JWT auth (access + refresh токены)
- [x] CRUD для вакансий (create/read/update/delete)
- [x] Geo-эндпоинты (поиск по радиусу, координаты через Nominatim)
- [x] Celery + Redis (фоновые задачи)
- [x] MinIO (S3-совместимый сторадж)
- [x] Healthcheck эндпоинт (GET /api/v1/health)
- [x] Миграции Alembic
- [x] Pydantic схемы (валидация ввода/вывода)
- [x] Обработка ошибок (HTTPException + кастомные эксепшены)

## База данных
- [x] PostgreSQL 16 + PostGIS 3.4
- [x] 15+ таблиц (users, vacancies, resumes, applications, companies и др.)
- [x] Пространственные индексы (GIST на координатах)
- [x] Сидинг тестовых данных
- [x] pg_dump backup (cron)

## Инфраструктура
- [x] Docker Compose (app, db, redis, minio, nginx, celery-worker, nominatim, osrm)
- [x] Nginx reverse proxy + HTTPS (Let's Encrypt)
- [x] Healthcheck для всех контейнеров
- [x] Мониторинг (cAdvisor + Node Exporter)
- [x] Backup cron (БД + файлы)
- [x] VPS 104.237.11.110

## Frontend
- [x] React 18 + TypeScript 5 (strict)
- [x] Vite 5 + Capacitor 6 (кроссплатформа)
- [x] PWA (vite-plugin-pwa, service worker)
- [x] MapLibre 4 (карты)
- [x] Tailwind CSS 3.4 + кастомная палитра
- [x] Zustand (state management: auth + theme)
- [x] Axios с JWT-интерсептором
- [x] LoginPage / RegisterPage (валидация, ошибки, роли)
- [x] Header (адаптив, тёмная тема, аватар-меню)
- [x] ProtectedRoute (JWT bootstrap через /auth/me)
- [x] Две темы (светлая/тёмная, localStorage + prefers-color-scheme)
- [x] Framber-motion анимации переходов
- [x] UI-примитивы: Button, Input, Avatar, AuthShell
- [x] TypeScript — 0 ошибок (`npx tsc --noEmit`)
- [x] Билд — успешно (CSS 98KB / gzip 14.7KB)
- [x] Карта MapLibre (MapContainer + маркеры)
- [x] Список вакансий с пагинацией
- [ ] Страница профиля (в работе — t_c33fdfe7)
- [ ] Интеграционные тесты (frontend → backend)
- [ ] E2E тесты (Playwright/Cypress)

## Тестирование
- [x] 18 pytest passed, 4 skipped (backend)
- [x] Vitest для frontend — 14 passed (Button, Input, Avatar)
- [ ] Интеграционные тесты API
