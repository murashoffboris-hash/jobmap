# JobMap — Кроссплатформенный сервис поиска работы по карте

MVP: веб-приложение с адаптивным интерфейсом, карта как основной экран, кроссплатформенная база (Flutter Web + мобильные сборки).

## Архитектура

```
Интернет
   |
   v
Nginx (reverse proxy, HTTPS)
   |
   +-- Frontend (Flutter Web / статический сайт)
   |
   +-- Backend API (FastAPI)
           |
           +-- PostgreSQL + PostGIS
           +-- Redis (cache, rate limit, queues)
           +-- Nominatim (геокодирование)
           +-- OSRM (маршруты)
           +-- S3-совместимое хранилище файлов
```

## Быстрый старт

```bash
cp .env.example .env
# Отредактируйте .env
docker compose up -d
```

## Документация

См. `docs/` — структура соответствует Obsidian-проекту `D:\Obsidian\HR\`.

## Стек

- **Frontend**: Flutter Web (адаптивный, единая кодовая база для Android/iOS)
- **Backend**: Python + FastAPI
- **База данных**: PostgreSQL 16 + PostGIS 3.4
- **Геосервисы**: Nominatim (геокодирование), OSRM (маршруты)
- **Кеш/очереди**: Redis + Celery/RQ
- **Proxy**: Nginx + Let's Encrypt
- **Хранение файлов**: S3-совместимое (MinIO / Supabase Storage)
