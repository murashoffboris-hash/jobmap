# 2026-07-23: Инфраструктура — SSL, мониторинг, backup

## Что сделано

### Созданы/изменены файлы

| Файл | Назначение |
|------|------------|
| `scripts/backup.sh` | Ежедневный backup PostgreSQL (pg_dump custom + SQL) |
| `scripts/setup-monitoring.sh` | Uptime Kuma + Docker log rotation + UFW + SSH hardening |
| `scripts/setup-full-infra.sh` | Полная настройка инфраструктуры (7 шагов) |
| `deploy/nginx/proxy.conf` | SSL-поддержка: listen 443 ssl, HTTP→HTTPS redirect |
| `.env.example` | Добавлен `LETSENCRYPT_EMAIL` |
| `docs/Развертывание/VPS 104.237.11.110.md` | Обновлён статус (SSL ✅, все healthy) |
| `docs/Развертывание/Реквизиты_доступа_VPS.md` | Добавлена инфраструктурная сводка |

### Уже было сделано (до этой задачи)
- Healthcheck'и в docker-compose.yml для всех 7 контейнеров (nginx, frontend, worker, backend, redis, minio, postgres)

## Развёртывание на VPS

VPS (`104.237.11.110`) недоступен из текущего окружения. Для применения на VPS:

```bash
# 1. Скопировать скрипты на VPS
scp -i ~/.ssh/vps_service247 scripts/*.sh root@104.237.11.110:/opt/jobmap/scripts/
scp -i ~/.ssh/vps_service247 deploy/nginx/proxy.conf root@104.237.11.110:/opt/jobmap/deploy/nginx/proxy.conf
scp -i ~/.ssh/vps_service247 .env.example root@104.237.11.110:/opt/jobmap/.env.example

# 2. Запустить полную настройку
ssh -i ~/.ssh/vps_service247 root@104.237.11.110 "cd /opt/jobmap && bash scripts/setup-full-infra.sh"

# 3. Перезапустить контейнеры с новым proxy.conf
ssh -i ~/.ssh/vps_service247 root@104.237.11.110 "cd /opt/jobmap && docker compose up -d"

# 4. Проверка
curl -sI https://phone.service247.by/health  # → 200
docker ps | grep healthy                      # → все 7 healthy
```

## Подробности

### SSL (Let's Encrypt)
- Сертификаты для `phone.service247.by` и `api.example.by`
- HTTP→HTTPS redirect (301)
- Автообновление через systemd timer (`certbot.timer`)
- Proxy.conf переписан: добавлен listen 443 ssl http2, ssl_certificate пути

### Backup
- Два формата: custom (pg_restore) и SQL (psql restore)
- Ротация: 7 дней
- Cron: ежедневно 3:00

### Мониторинг
- Uptime Kuma на 127.0.0.1:3001 (через SSH tunnel)
- Мониторы: /health (backend), frontend POST
- Telegram alerts

### Безопасность
- UFW: только OpenSSH, 80, 443
- SSH: PasswordAuthentication no, PermitRootLogin prohibit-password
- Fail2Ban: защита от brute-force
- Docker log rotation: max 10m, 3 файла
