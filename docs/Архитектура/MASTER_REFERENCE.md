# JobMap — Master Reference: Agents, Rules, Configs

> Создан: 29.07.2026 07:00 RTZ
> Назначение: единый файл для анализа эффективности, безопасности разработки в JobMap.
> Все промпты агентов (SOUL.md), правила проекта (AGENTS.md + TEAM_PLAYBOOK), конфигурации.

---

## ЧАСТЬ 1. КОМАНДА АГЕНТОВ

### 1.1. Таблица профилей

| # | Профиль | Провайдер | Модель | Fallback → | Fallback → |
|---|---------|-----------|--------|------------|------------|
| 1 | hr-orchestrator | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax/MiniMax-M3 |
| 2 | hr-change-manager | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 3 | hr-product-analyst | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 4 | hr-architect | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 5 | hr-backend-programmer | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 6 | hr-backend-programmer-2 | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 7 | hr-frontend-programmer | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 8 | hr-frontend-programmer-2 | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 9 | hr-integration-devops | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 10 | hr-code-reviewer | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 11 | hr-qa-engineer | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 12 | hr-security-reviewer | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |
| 13 | hr-documenter | deepseek | deepseek-v4-pro | kimi/kimi-k3 | minimax |

### 1.2. SOUL.md агентов

---

#### hr-orchestrator
**Роль:** Оркестратор команды. Единая точка взаимодействия пользователя с командой.

**Область:** приём ТЗ, декомпозиция, маршрутизация задач, контроль зависимостей, эскалация, отчёты.

**Запрещено:** писать код, делать merge, code review, документацию (вместо documenter), пропускать этапы workflow.

---

#### hr-change-manager
**Роль:** Классификация запросов, приоритизация.

**Область:** приём от оркестратора → классификация (feature/bug/refactor/hotfix) → приоритет → оценка scope.

---

#### hr-product-analyst
**Роль:** Формализация требований в user stories + acceptance criteria.

**Область:** анализ запросов → спецификации → edge cases → передача architect.

---

#### hr-architect
**Роль:** Архитектура системы, ADR, технические стандарты.

**Область:** проектирование компонентов → ADR → паттерны → выбор технологий.

---

#### hr-backend-programmer
**Роль:** Backend-разработка (FastAPI + PostgreSQL + PostGIS).

**Область:** API endpoints, бизнес-логика, миграции Alembic, работа с БД, интеграции.

**Запрещено:** править frontend, nginx без devops, коммитить .env, push --force.

---

#### hr-backend-programmer-2 (дублёр)
**Роль:** То же что backend-programmer. Специализация: performance, Redis, connection pool.

---

#### hr-frontend-programmer
**Роль:** Frontend-разработка (React 18 + TypeScript + Vite + Capacitor + MapLibre).

**Область:** UI-компоненты, работа с API, карты, mobile (Capacitor), PWA.

**Запрещено:** править backend, nginx без devops, ломать типы TypeScript.

---

#### hr-frontend-programmer-2 (дублёр)
**Роль:** То же что frontend-programmer. Специализация: UI/UX, accessibility, mobile-first.

---

#### hr-integration-devops
**Роль:** CI/CD, Docker, VPS, деплой, nginx, мониторинг.

**Область:** пайплайны, контейнеры, развёртывание, reverse proxy, БД, секреты.

**Запрещено:** коммитить секреты, деплоить без тестов, менять код приложений.

---

#### hr-code-reviewer
**Роль:** Независимая проверка кода (другая модель — MiniMax-M3).

**Область:** ревью backend + frontend, архитектура, стандарты, баги, уязвимости.

**Запрещено:** писать код, approve свой же код, пропускать security-проверки.

---

#### hr-qa-engineer
**Роль:** Тестирование (unit, integration, E2E).

**Область:** тесты backend (pytest) + frontend (vitest), ручное тестирование, acceptance criteria.

---

#### hr-security-reviewer
**Роль:** Аудит безопасности.

**Область:** уязвимости (SQLi, XSS, CSRF), секреты, аутентификация, авторизация, deps audit.

---

#### hr-documenter
**Роль:** Техническая документация.

**Область:** Obsidian, README, API docs, инструкции, changelog, архитектурные схемы.

---

## ЧАСТЬ 2. ПРАВИЛА ПРОЕКТА (AGENTS.md)

### 2.1. Архитектура

| Компонент | Стек |
|-----------|------|
| Backend | FastAPI + SQLAlchemy + PostgreSQL 16 + PostGIS 3.4 + Redis 7 + Celery + MinIO |
| Frontend | React 18 + TypeScript 5 + Vite 5 + Capacitor 6 + PWA + MapLibre 4 |
| Инфра | Docker Compose, Nginx, Let's Encrypt |
| VPS | 104.237.11.110 (Ubuntu 24.04, 4 CPU, 5.7G RAM, 28G disk) |
| Гео | Self-hosted: Nominatim (BY), OSRM (BY), Tileserver (mbtiles 371MB) |

### 2.2. Git

- Коммиты на **русском**, формат: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `infra:`
- **НЕ** использовать `--force`, `--amend`, `rebase` без разрешения
- Ветки: `feature/<name>`, `fix/<name>`
- Защищённая ветка: `main`

### 2.3. Obsidian (документация)

```
D:\Obsidian\HR\
├── 00_Паспорт проекта.md
├── 01_Архитектура/        ← MAP_ARCHITECTURE.md, PROJECT_DIGEST.md
├── 02_Требования/
├── 03_Задачи/
├── 04_ADR/
├── 05_Развертывание/      ← Реквизиты_доступа_VPS.md, CI_CD.md
├── 06_Журнал изменений/
├── 07_Интеграции/
├── 08_Тестирование/
├── 09_Проверки Review/
├── 10_Известные проблемы/
├── 11_Релизы/
├── 12_Аудиты/
└── docs/Архитектура/      ← TEAM_PLAYBOOK.md, TEAM_CONFIG_SNAPSHOT.md
```

### 2.4. Kanban Workflow (21 статус)

```
BACKLOG → DISCOVERY → READY_FOR_ANALYSIS → ANALYSIS → READY_FOR_ARCHITECTURE →
ARCHITECTURE → READY_FOR_DEVELOPMENT → DEVELOPMENT → READY_FOR_REVIEW → REVIEW →
CHANGES_REQUIRED → READY_FOR_QA → QA → READY_FOR_DOCUMENTATION → DOCUMENTATION →
READY_FOR_INTEGRATION → INTEGRATION → READY_FOR_USER_ACCEPTANCE → DONE
BLOCKED / CANCELLED
```

### 2.5. Definition of Done

Задача считается выполненной когда пройдены ВСЕ этапы:
1. Требования формализованы (product-analyst)
2. Архитектурные решения согласованы (architect)
3. Код реализован (programmer)
4. Commit по правилам
5. Тесты написаны и пройдены (qa-engineer)
6. Code review → APPROVED (code-reviewer)
7. Security review (если требуется)
8. Документация обновлена (documenter)
9. Obsidian обновлён
10. Интеграция завершена (devops)

---

## ЧАСТЬ 3. TEAM_PLAYBOOK (выжимка 20 правил)

### Правила, обязательные с первого дня:

1. **goal_mode=True** на сложных задачах → −80% потерь iteration budget
2. **Сам-мерж** воркером (после build+тесты) → −90% латентности deploy
3. **Fallback-провайдеры** (≥2 в каждом профиле) → −90% простоев
4. **failure_limit = 4** → −70% ложных крашей
5. **Gateway watchdog** (cron, 5 мин) → −95% простоев gateway
6. **Project digest** (PROJECT_DIGEST.md, 3-6KB) → −20-30 итераций разведки
7. **Дублёры профилей** при ≥5 blocked задач → +25-35% пропускная способность

### Правила, внедряемые по мере роста:

8. **CI/CD** (GitHub Actions) → −30-40% времени команды на деплой
9. **Ежедневная отмена дублей** в blocked → −5-10 мин/день
10. **nginx CSP: НЕ сужать** → предотвращает 90% багов «карта серая»
11. **PWA: force cache bust** при каждом релизе → −100% багов «у меня старое»
12. **Geo self-hosting: порядок деплоя** → Nominatum после OSRM (RAM)
13. **CSS-фреймворк фиксировать сразу** → −1 день на унификацию
14. **Cron-доставка: всегда origin + attach_to_session** → нет потерянных докладов
15. **Memory: declarative facts, не инструкции** → чище контекст
16. **Worker «не может» → kanban_block сразу** → не держать в ожидании
17. **Documentation sync: .env → Obsidian** → нет расхождений через 2 недели
18. **dev vs prod: не смешивать** → staging при росте

---

## ЧАСТЬ 4. КОНФИГУРАЦИЯ KANBAN

| Параметр | Значение |
|----------|----------|
| Доска | hr-project |
| failure_limit | **4** |
| goal_mode | по умолчанию для задач >1 день |
| Workflow | 21 статус |
| Dispatch interval | ~60 сек |

---

## ЧАСТЬ 5. ИНФРАСТРУКТУРА

### 5.1. VPS (104.237.11.110)

| Ресурс | Значение |
|--------|----------|
| CPU | 4 cores |
| RAM | 5.7 GB (2.6G used, 3.1G free) |
| Disk | 28 GB (21G used, 5.6G free) |
| Docker | 11 контейнеров |

### 5.2. Домены

| Домен | Назначение |
|-------|------------|
| phone.service247.by | Основной сайт (HTTPS) |
| api.phone.service247.by | API (HTTPS) |

### 5.3. Сервисы (Docker)

| Контейнер | RAM | Порт |
|-----------|-----|------|
| jobmap-backend | 237M | :8000 |
| jobmap-frontend | 8M | :80 |
| jobmap-nginx | 10M | :443 |
| jobmap-postgres | 51M | :5432 |
| jobmap-redis | 11M | :6379 |
| jobmap-nominatim | 1.2G | :8080 |
| jobmap-osrm | — | :5000 |
| jobmap-tileserver | 138M | :8080 |
| jobmap-grafana | 83M | :3001 |
| jobmap-loki | 76M | :3100 |
| jobmap-prometheus | 43M | :9090 |

---

## ЧАСТЬ 6. КАРТА (MAP_ARCHITECTURE)

### 6.1. Цепочка

```
Браузер → nginx:443 → /tiles/ → tileserver:8080 → belarus.mbtiles (371MB, 150K tiles)
                    → /data/  → tileserver:8080/data/
                    → /fonts/ → cartocdn (proxy)
                    → /maps/  → positron-style.json (статический)
```

### 6.2. Диагностика (4 шага)

1. `curl /maps/positron-style.json` → 200
2. `curl /tiles/data/v3.json` → tiles URL = `https://phone.service247.by/...`
3. `curl /data/v3/11/1180/660.pbf --compressed` → 12KB
4. `curl /fonts/Noto Sans Regular/0-255.pbf` → 200

### 6.3. CSP (НЕ сужать!)

```
script-src 'self' 'unsafe-eval' blob:
worker-src 'self' blob:
img-src 'self' data: blob: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com
connect-src 'self' https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://phone.service247.by
```

---

## ЧАСТЬ 7. CI/CD

| Параметр | Статус |
|----------|--------|
| Workflow файл | ✅ `.github/workflows/deploy.yml` |
| GitHub Secrets | ✅ VPS_HOST, VPS_USER, VPS_SSH_KEY |
| Триггер | push в main + workflow_dispatch |
| Авто-деплой | ❌ **НЕ активирован** |
| Ручной деплой | ~20 мин (tar+scp+docker restart) |

### Команда для ручного запуска:
```
https://github.com/murashoffboris-hash/jobmap/actions
→ Deploy JobMap to VPS → Run workflow → main
```

---

## ЧАСТЬ 8. СВОДНАЯ ОЦЕНКА

| Критерий | Оценка | Узкое место |
|----------|--------|-------------|
| **Эффективность** | 🟢 85% (8/12 профилей, 0% idle) | CI/CD не активирован |
| **Безопасность** | 🟡 70% (CSP, HTTPS, JWT ok) | ILIKE-поиск не аудирован |
| **Скорость** | 🟢 80% (2x от playbook) | Review bottleneck + ручной деплой |

**Ближайшие шаги для выхода на 95%+:** активировать CI/CD, разрешить self-merge, восстановить watchdog.

---

*Последнее обновление: 29.07.2026 07:00 RTZ*
*Источники: SOUL.md × 13, AGENTS.md, TEAM_PLAYBOOK.md, TEAM_CONFIG_SNAPSHOT.md, MAP_ARCHITECTURE.md, PROJECT_DIGEST.md*
