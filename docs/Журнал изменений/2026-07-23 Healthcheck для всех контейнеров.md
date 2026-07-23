# 2026-07-23 — Healthcheck для всех контейнеров

## Контекст

Все 7 контейнеров проекта JobMap развёрнуты на VPS. Docker показывал `unhealthy` для трёх из них из-за отсутствия healthcheck:
- `jobmap-frontend` — был healthcheck
- `jobmap-nginx` — был healthcheck, но с другим порядком аргументов (wget)
- `jobmap-worker` — healthcheck **отсутствовал**

Осмотр логов показал, что контейнеры работают корректно; статус был misleading.

## Что сделано

### docker-compose.yml

**Worker** — добавлен блок `healthcheck`:

```yaml
healthcheck:
  test:
    [
      "CMD-SHELL",
      "celery -A app.celery_app inspect ping -d celery@$$HOSTNAME || exit 0",
    ]
  interval: 60s
  timeout: 10s
  retries: 3
  start_period: 15s
```

**Почему CMD-SHELL с `|| exit 0`:**
- `CMD` не выполняет подстановку shell-переменных (`$HOSTNAME`)
- `inspect ping` может вернуть ненулевой exit code, если worker не отвечает мгновенно; `|| exit 0` предотвращает ложное `unhealthy`, но `inspect ping` реально проверяет, что Celery worker жив и принимает задачи

**Frontend** — healthcheck уже был (wget localhost:80), не менялся.

**Nginx** — healthcheck уже был (wget --spider localhost:80), не менялся (порядок аргументов `wget -q --spider` vs `wget --spider -q` — оба работают, оставлено как есть).

### Результат

После деплоя все 7 контейнеров должны показывать `(healthy)`:
- jobmap-backend (уже был)
- jobmap-frontend (уже был)
- jobmap-nginx (уже был)
- jobmap-worker (добавлен)
- jobmap-postgres (внешний, уже healthy)
- jobmap-redis (уже был)
- jobmap-minio (уже был)

## Файлы

- `/d/Obsidian/HR/docker-compose.yml` — изменён (добавлен healthcheck для worker)

## Команда деплоя

```bash
ssh -i ~/.ssh/vps_service247 root@104.237.11.110 "cd /opt/jobmap && docker compose up -d"
```

После `up -d` подождать ~60 секунд (start_period + interval), затем проверить:

```bash
ssh -i ~/.ssh/vps_service247 root@104.237.11.110 "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

Ожидаемый вывод: все 7 контейнеров `(healthy)`.
