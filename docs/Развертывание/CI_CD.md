# CI/CD — автоматический деплой через GitHub Actions

> Последнее обновление: 2026-07-27  
> Ветка: `feature/cicd-github-actions` → `infra/initial-audit`

## Обзор

Автоматический деплой фронтенда и бэкенда на VPS `104.237.11.110` при push в ветку `infra/initial-audit`. Время от push до продакшна: **≤ 5 минут**.

## Как работает

```
push в infra/initial-audit
  → GitHub Actions runner (ubuntu-latest)
    → npm ci + npm run build (фронтенд)
    → проверка синтаксиса Python (бэкенд)
    → scp frontend/dist/ → VPS
    → scp backend/app/ → VPS
    → docker compose build --no-cache backend
    → docker compose up -d backend frontend
    → health check + smoke test
```

## Триггеры

| Событие | Срабатывает? |
|---------|-------------|
| `push` в `infra/initial-audit` | ✅ Да |
| `workflow_dispatch` (ручной запуск) | ✅ Да |
| PR в `infra/initial-audit` | ❌ Нет |
| `push` в другие ветки | ❌ Нет |

## Ручной запуск

Зайти в GitHub → Actions → "Deploy JobMap to VPS" → Run workflow.

Опция `skip_tests` — пропустить тесты (зарезервировано, пока тестов в workflow нет).

## GitHub Secrets

Перед первым деплоем настроить секреты в Settings → Secrets and variables → Actions:

| Secret | Значение | Комментарий |
|--------|----------|-------------|
| `VPS_HOST` | `104.237.11.110` | IP сервера |
| `VPS_USER` | `root` | Пользователь |
| `VPS_SSH_KEY` | содержимое `~/.ssh/jobmap_auto` | Приватный ключ (без passphrase) |

Команда для получения ключа:
```bash
cat ~/.ssh/jobmap_auto
```

## Откат

Если деплой упал — автоматический откат на предыдущий коммит (`HEAD~1`):
- `git checkout HEAD~1`
- `docker compose build --no-cache backend`
- `docker compose up -d backend frontend`

Ручной откат:
```bash
ssh root@104.237.11.110
cd /opt/jobmap
git log --oneline -5       # найти нужный коммит
git checkout <commit-hash>
docker compose build --no-cache backend
docker compose up -d backend frontend
```

## Smoke-тесты

После каждого деплоя:
```bash
# Health check
curl -s https://phone.service247.by/health
# → {"status":"healthy"}

# API vacancies
curl -s https://phone.service247.by/api/vacancies?page_size=1
# → {"items":[...],"total":N}
```

## Отладка

### Проверить статус последнего run'а
GitHub → Actions → последний run → логи по шагам.

### Посмотреть логи на VPS
```bash
ssh root@104.237.11.110
docker compose -f /opt/jobmap/docker-compose.yml logs --tail=100 backend
docker compose -f /opt/jobmap/docker-compose.yml logs --tail=100 frontend
```

### Проверить что контейнеры запущены
```bash
ssh root@104.237.11.110 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### Локальная проверка workflow
```bash
# Установить act (эмулятор GitHub Actions)
# https://github.com/nektos/act
act push -j deploy
```

## Известные ограничения

- Alembic-миграции не настроены (нет `backend/alembic.ini`). Шаг миграций пропущен.
- Бэкенд пересобирается с `--no-cache` на каждом деплое (~60–90 сек).
- Фронтенд — статическая раздача через nginx:alpine (volume mount), Docker-образ не пересобирается.
- При падении VPS (недоступен по SSH) — workflow падает, ручной деплой обязателен.

## Безопасность

- SSH-ключ **только** в GitHub Secrets, **никогда** в репозитории.
- Workflow **не логирует** `.env`, пароли, JWT-секреты.
- Используются проверенные actions: `checkout@v4`, `setup-node@v4`, `scp-action@v0.1.7`, `ssh-action@v1.2.2`.
- SCP и SSH только по ключу (port 22), без пароля.

## Файлы

| Файл | Назначение |
|------|-----------|
| `.github/workflows/deploy.yml` | Workflow авто-деплоя |
| `docs/Развертывание/CI_CD.md` | Эта документация |
| `docs/Развертывание/Реквизиты_доступа_VPS.md` | Реквизиты VPS |
| `docs/Развертывание/VPS 104.237.11.110.md` | Детали сервера |
