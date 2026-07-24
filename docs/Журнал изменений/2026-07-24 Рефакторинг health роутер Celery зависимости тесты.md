# 2026-07-24 Рефакторинг: health-роутер, Celery, зависимости, тесты

## Что сделано

### 1. 🔴 Исправлен health-роутер (дублирование)
**Проблема:** В `routers/__init__.py` была урезанная версия health-роутера (все проверки возвращали `"pending"`), а реальный код с проверками PostGIS/Redis/Nominatim/OSRM лежал рядом в `health.py`. main.py подхватывал заглушку из `__init__.py`.

**Решение:**
- `routers/__init__.py` переписан — содержит полный health-роутер с реальными проверками зависимостей
- Файл `routers/health.py` удалён (дубликат)
- Теперь `/health` возвращает:
  - `postgresql`: реальный ответ PostGIS через asyncpg
  - `redis`: ping
  - `nominatim`: /status.php
  - `osrm`: /version
  - Итоговый статус: `"ok"` (все зелёные) или `"degraded"`

### 2. 🔴 Создан `celery_app.py`
**Проблема:** В `docker-compose.yml` worker запускался как `celery -A app.celery_app worker`, но файл `app/celery_app.py` не существовал — healthcheck упал бы на старте.

**Решение:**
- Создан `backend/app/celery_app.py` — Celery-приложение с:
  - broker/backend = Redis (из settings)
  - Сериализация JSON
  - Timezone Europe/Minsk
  - task_track_started, soft/time limits, max_tasks_per_child
  - `debug_task` — верификация live-воркера

### 3. 🟡 Вынесен `get_session()` в общий `dependencies.py`
**Проблема:** Функция `get_session()` была объявлена в 3 роутерах (WET = Write Everything Twice).

**Решение:**
- Создан `backend/app/dependencies.py` — единственный источник `get_session()`
- `routers/auth.py`, `routers/vacancies.py`, `routers/geoservices.py` — импортируют из `dependencies`
- Удалены локальные копии `get_session()` из всех трёх роутеров

### 4. 🟡 Создан `services/vacancies.py`
**Проблема:** Бизнес-логика вакансий (геопоиск, создание, обновление с геокодингом) была в роутере, нарушая Single Responsibility Principle.

**Решение:**
- Создан `backend/app/services/vacancies.py` с функциями:
  - `vacancy_to_response(v)` — конвертация ORM → Pydantic
  - `geo_search(session, lat, lon, radius, ...)` — PostGIS поиск
  - `create_vacancy(session, data, owner_id)` — создание с геокодингом
  - `update_vacancy(session, vacancy, data)` — обновление с ре-геокодингом
  - `_apply_geo(vacancy, geo)` — общий хелпер применения гео-данных
- `routers/vacancies.py` переписан — только FastAPI-декораторы, вызовы сервиса и ownership check

### 5. 🟡 Добавлен `pytest.ini`
**Проблема:** Не было конфигурации pytest — `asyncio_mode` не задан, тесты могли работать нестабильно.

**Решение:**
- Создан `backend/pytest.ini` с:
  - `asyncio_mode = auto`
  - `testpaths = tests`
  - Явные маркеры

## Изменённые файлы

| Файл | Действие | Описание |
|------|----------|----------|
| `backend/app/routers/__init__.py` | перезапись | Полный health-роутер вместо заглушки |
| `backend/app/routers/health.py` | **удалён** | Дубликат — больше не нужен |
| `backend/app/celery_app.py` | **создан** | Celery worker-приложение |
| `backend/app/dependencies.py` | **создан** | Общий get_session() |
| `backend/app/routers/auth.py` | изменён | Импорт get_session из dependencies |
| `backend/app/routers/geoservices.py` | изменён | Импорт get_session из dependencies |
| `backend/app/routers/vacancies.py` | переписан | SRP: тонкий роутер, логика в сервисе |
| `backend/app/services/vacancies.py` | **создан** | Бизнес-логика вакансий |
| `backend/pytest.ini` | **создан** | asyncio_mode = auto |

## Затрагивает
- `backend/app/`
- `backend/pytest.ini`

## Следующий шаг
- Запустить тесты (`pytest tests/ -v`) — ожидается 18 passed, 4 skipped
- Дописать ADR для архитектурных решений
- Добавить unique constraint на `chats` и `reviews` (LOW)
