# Карта в JobMap — полная схема для диагностики

> Создано: 2026-07-27 после серии инцидентов с отображением.
> Цель: при следующей проблеме «карта не показывается» — открыть этот файл, найти нужный слой, проверить.

---

## Общая архитектура (3 уровня)

```
┌─────────────────────────────────────────────────────────────┐
│ БРАУЗЕР ПОЛЬЗОВАТЕЛЯ                                        │
│   https://phone.service247.by/                                │
│   MapLibre GL JS (frontend, бандл 808 КБ)                    │
│   Запрашивает: style.json → tiles → glyphs                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ HTTPS (Let's Encrypt)
┌─────────────────────────────────────────────────────────────┐
│ VPS 104.237.11.110                                          │
│                                                             │
│   ┌─── nginx:443 (Docker, jobmap-nginx) ──────────────┐    │
│   │   • TLS termination (Let's Encrypt cert)            │    │
│   │   • Reverse proxy для всех сервисов                 │    │
│   │   • sub_filter: переписывает URL в style.json       │    │
│   │     (internal:8080 → /tiles/)                      │    │
│   └─────────────────────────────────────────────────────┘    │
│       │       │        │         │         │                  │
│       ▼       ▼        ▼         ▼         ▼                  │
│   frontend  backend  nominatim  osrm   tileserver             │
│   :3000    :8000    :8080      :5000   :8080                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼ Docker network
┌─────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                  │
│   /opt/geo/belarus.mbtiles (371 МБ, 150 083 тайлов)         │
│   /opt/geo/belarus.osm.pbf (347 МБ исходник)                │
│   /opt/geo/belarus.osrm.* (OSRM extract)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Компоненты подробно

### 1. MapLibre GL JS (фронтенд)
- **Файл**: `frontend/src/components/MapContainer.tsx` + `MapPicker.tsx`
- **Стиль по умолчанию**: `VITE_MAP_STYLE_URL=/maps/positron-style.json` (из `.env`)
- **Fallback chain**: `/maps/positron-style.json` → `/tiles/style.json` → `basemaps.cartocdn.com/...`
- **Зависимости**: `maplibre-gl@4.x` (1.3 МБ в bundle)

### 2. nginx (`jobmap-nginx` контейнер, порт 443)
- **Конфиг**: `/opt/jobmap/deploy/nginx/proxy.conf`
- **TLS**: `ssl_certificate /etc/letsencrypt/live/phone.service247.by/fullchain.pem`
- **Ключевые locations**:
  - `location /` → `proxy_pass http://frontend` (статика SPA)
  - `location /api/` → `proxy_pass http://backend:8000` (FastAPI)
  - `location /tiles/` → `proxy_pass http://tileserver:8080/` + `sub_filter` для переписывания URL
  - `location /data/` → `proxy_pass http://tileserver:8080/data/`
  - `location /fonts/` → `proxy_pass https://tiles.basemaps.cartocdn.com/fonts/`
  - `location /maps/` → статические файлы (positron-style.json) из `/opt/jobmap/frontend/dist/maps/`
- **CSP**: `connect-src 'self' https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org`

### 3. tileserver-gl (`jobmap-tileserver` контейнер, порт 8080)
- **Образ**: `maptiler/tileserver-gl` (или klokantech)
- **Данные**: `/data/belarus.mbtiles` (OpenMapTiles schema, tilemaker generated)
- **Внутренние endpoints** (НЕ доступны снаружи напрямую, только через nginx):
  - `GET /` — визуализатор tileserver (свой мини-интерфейс)
  - `GET /styles/jobmap/style.json` — наш стиль «Basic preview»
  - `GET /data/v3.json` — tilejson
  - `GET /data/v3/{z}/{x}/{y}.pbf` — vector tiles
  - `GET /styles/{style}/style.json` — другие стили (basic, bright, etc)
- **XYZSCHEMA**: использует XYZ (не TMS). Минск z11 ≈ x=1180, y=660.

### 4. Стили карты (2 штуки)

#### a. `frontend/public/maps/positron-style.json` (свой, основной)
- 50 слоёв
- Светло-серая цветовая схема (CARTO/MapTiler Positron, CC-BY)
- Глифы: `glyphs: /fonts/{fontstack}/{range}.pbf`
- Source: наш tileserver
- Лицензия: CC-BY 3.0 (требует attribution в UI)

#### b. `tileserver /styles/jobmap/style.json` (basic preview, fallback)
- 47 слоёв
- Тёплый бежевый (hsl 47°, 26%, 88%)
- Минимальные слои: landuse, water, place
- **Не используется в проде** — MapContainer сначала пробует Positron

---

## Цепочка запросов (что происходит при загрузке карты)

```
1. Браузер загружает https://phone.service247.by/
   → HTML + JS bundle (maplibre-gl 1.3 МБ)
2. React инициализирует MapContainer
3. MapContainer читает VITE_MAP_STYLE_URL = "/maps/positron-style.json"
4. GET /maps/positron-style.json
   → nginx отдает статику из dist/maps/
5. MapLibre парсит style.json:
   - sources.openmaptiles.url = "/tiles/data/v3.json"
   - glyphs = "/fonts/{fontstack}/{range}.pbf"
6. GET /tiles/data/v3.json
   → nginx → tileserver:8080/data/v3.json
7. tilejson возвращает: tiles = "http://phone.service247.by/data/v3/{z}/{x}/{y}.pbf"
8. MapLibre вычисляет нужные тайлы для viewport + zoom
9. GET /data/v3/11/1180/660.pbf
   → nginx → tileserver:8080/data/v3/11/1180/660.pbf
   → tileserver читает из mbtiles → gzip → 12-25 КБ
10. MapLibre рендерит слои
11. Для слоёв с text-field → GET /fonts/Noto Sans Regular/0-255.pbf
    → nginx → cartocdn.com (proxy)
    → 41 КБ, gzip
12. Карта появляется
```

---

## Диагностика по слоям

### Проблема: «Карта не отображается (серый экран)»

**Шаг 1. Проверить style.json доступен:**
```bash
curl -sI https://phone.service247.by/maps/positron-style.json
# Ожидаем: HTTP 200, Content-Type: application/json
```

**Шаг 2. Проверить tilejson:**
```bash
curl -s https://phone.service247.by/tiles/data/v3.json | head -c 200
# Должен вернуть JSON с "tiles" массивом
```

**Шаг 3. Проверить тайл (Минск z=11):**
```bash
curl -s --compressed -o /tmp/t.bin -w "HTTP %{http_code}, size: %{size_download} bytes\n" \
  https://phone.service247.by/data/v3/11/1180/660.pbf
# Ожидаем: 200, ~12 КБ
```

**Шаг 4. Проверить глиф:**
```bash
curl -s --compressed -o /dev/null -w "HTTP %{http_code}\n" \
  https://phone.service247.by/fonts/Noto%20Sans%20Regular/0-255.pbf
# Ожидаем: 200
```

**Шаг 5. Браузер: F12 → Console → красные строки**
Типичные ошибки:
- `Refused to connect to ...` — CSP блокирует (проверить nginx CSP)
- `Failed to fetch style.json` — network/SSL проблема
- `WebGL: could not initialize` — браузер не поддерживает (IE, очень старые)
- `CORS` — если upstream отдает без `Access-Control-Allow-Origin`

---

### Проблема: «Карта отображается, но без подписей улиц»

**Причина: глифы (шрифты) не загрузились.** MapLibre пропускает text-слои.

**Проверка:**
```bash
# 4 диапазона глифов должны быть 200
for r in "0-255" "256-511" "8192-8447" "65280-65535"; do
  curl -s --compressed -o /dev/null -w "$r: HTTP %{http_code}\n" \
    "https://phone.service247.by/fonts/Noto%20Sans%20Regular/$r.pbf"
done
```

**Если 200 только на 0-255:** другие диапазоны не кешированы у cartodb. Решение: добавить свой glyph-сервер.

**Если все 4xx:** upstream cartodb мёртв (был случай 25.07.2026 — переключили на cloudfront). Альтернативы:
- `https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf`
- `https://fonts.openstreetmap.org/...` (если поднимем свои)

---

### Проблема: «Серый фон, но в Network тайлы 200, идут»

**Причина 1: MapLibre не может декодировать PBF.** Проверить:
```bash
# Скачать и попробовать распарсить
curl -s --compressed https://phone.service247.by/data/v3/11/1180/660.pbf -o /tmp/t.pbf
# Если файл 0 байт или мусор — tileserver кривой
file /tmp/t.pbf
# Ожидаем: data (не text/html)
```

**Причина 2: mbtiles не содержит нужный тайл** (XYZSCHEMA не совпадает). Проверить напрямую:
```bash
ssh -i ~/.ssh/jobmap_auto root@104.237.11.110 \
  "docker exec jobmap-tileserver sh -c 'wget -q -O - http://localhost:8080/data/v3/11/1180/660.pbf | wc -c'"
# Должно быть >1000
```

**Причина 3: style.json не подходит к нашему mbtiles** (другая schema слоёв). Проверить:
```bash
# Скачать наш mbtiles metadata
curl -s https://phone.service247.by/tiles/data/v3.json | head -c 500
# Должен содержать vector_layers: place, boundary, transportation, etc
```

---

### Проблема: «Подложка серая, но вижу белые прямоугольники (как tiles, но пустые)»

**Причина: загружается tileserver /styles/jobmap/style.json вместо Positron.** Этот стиль использует минимальные слои, отсюда «пустые» полигоны.

**Проверить какой стиль реально отдаётся:**
- F12 → Network → фильтр style.json
- Должен быть `https://phone.service247.by/maps/positron-style.json`
- Если другой — проверить `.env` (`VITE_MAP_STYLE_URL`)

---

## Файлы конфигурации

### Frontend
| Файл | Что |
|------|-----|
| `frontend/.env` | `VITE_MAP_STYLE_URL=/maps/positron-style.json` |
| `frontend/src/components/MapContainer.tsx` | Инициализация карты |
| `frontend/src/components/MapPicker.tsx` | Мини-карта в форме вакансии |
| `frontend/public/maps/positron-style.json` | Positron стиль (50 слоёв) |

### Backend
| Файл | Что |
|------|-----|
| `backend/app/services/geo.py` | Геокодинг (Nominatim) |
| `backend/app/services/osrm.py` | Маршруты (OSRM) |
| `backend/app/routers/geo.py` | `/api/geo/geocode`, `/api/geo/reverse` |

### Инфра
| Файл | Что |
|------|-----|
| `deploy/nginx/proxy.conf` | nginx, **КРИТИЧЕН** для карты |
| `docker-compose.yml` | Сервисы tileserver, nominatim, osrm |
| `/opt/geo/belarus.mbtiles` | Данные тайлов (371 МБ) |

---

## Сервисы и их здоровье

### Проверить все сразу:
```bash
ssh -i ~/.ssh/jobmap_auto root@104.237.11.110 'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "tileserver|nginx|nominatim|osrm|backend|frontend"'
```

### Ожидаемый вывод:
```
jobmap-tileserver   Up 2 days (healthy)
jobmap-nginx        Up 2 days (healthy)
jobmap-nominatim    Up 2 days (healthy)
jobmap-osrm         Up 2 days
jobmap-backend      Up 2 days
jobmap-frontend     Up 2 days
```

### Перезапуск tileserver (если нужно):
```bash
ssh -i ~/.ssh/jobmap_auto root@104.237.11.110 'docker restart jobmap-tileserver && sleep 5'
```

### Логи tileserver:
```bash
ssh -i ~/.ssh/jobmap_auto root@104.237.11.110 'docker logs jobmap-tileserver --tail 50'
```

Типичные запросы в логах:
- `GET /data/v3/11/1180/660.pbf 200 12964` — нормальный тайл
- `GET /data/fonts/Noto Sans Regular/0-255.pbf 404` — у tileserver нет своих глифов (это нормально, они через nginx)
- `GET /styles/jobmap/style.json 200 14726` — стиль (через визуализатор)

---

## CSP и безопасность

Текущий CSP в `proxy.conf`:
```
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data: https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com;
connect-src 'self' https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org;
frame-ancestors 'self';
```

**НИКОГДА не сужать CSP.** Старые SW-бандлы пользователей перестают работать (инцидент 26.07).

Если нужно разрешить новый домен (например, для шрифтов), **добавь** в `connect-src` и `img-src`:
```
connect-src 'self' <existing> <new-domain>;
```

---

## Известные ограничения

1. **tileserver сам не имеет глифов** — отдаёт 404 на `/data/fonts/...`. Решение: nginx проксирует `/fonts/` на cartodb.
2. **mbtiles генерировался через `tilemaker`** — поля называются `name:latin` (не `name`). Positron стиль это учитывает (`{name:latin}`), а basic-preview tileserver — нет (отсюда серый).
3. **Данные устаревают** — обновлять раз в месяц с Geofabrik Belarus.
4. **Один tileserver на весь РБ** — при 100+ одновременных пользователях может упереться. Решение: горизонтальное масштабирование (отдельная задача).
5. **Карта не работает в IE** — MapLibre требует WebGL (IE нет).
6. **Service Worker отключён (28.07.2026)** — `vite.config.ts: disable: true` после инцидента с кэшированием старого CSP. Планируется PWA v2 с версионированным SW.
7. **CSP worker-src обязателен** — `script-src 'self'` без явного `worker-src` неявно блокирует Web Worker MapLibre. Текущая CSP: `worker-src 'self' blob:; script-src 'self' 'unsafe-eval' blob:; img-src 'self' data: blob: ...`. **НЕ удалять blob: и unsafe-eval** — MapLibre сломается.
8. **TileJSON https через X-Forwarded-Proto** — tileserver строит абсолютный URL с `req.headers.host` + `req.protocol`. Без `proxy_set_header X-Forwarded-Proto https` отдаёт `http://...` → Mixed Content. **НЕ убирать** эти заголовки из proxy.conf.

---

## Связь с другими сервисами

| Сервис | Зачем | Если падает |
|--------|-------|-------------|
| Nominatim | Геокодинг (адрес → координаты) | Карта работает, но форма вакансий не работает |
| OSRM | Маршруты | Не критично для отображения |
| PostgreSQL/PostGIS | Хранение вакансий, пользователей | Карта работает, но точек нет |
| Redis | Кэш геокодинга | Карта работает медленнее |

---

## Быстрая шпаргалка (TL;DR)

**Карта не отображается:**
1. `curl /maps/positron-style.json` → 200?
2. `curl /data/v3.json` → 200?
3. `curl /data/v3/11/1180/660.pbf --compressed` → 12 КБ?
4. `curl /fonts/Noto Sans Regular/0-255.pbf` → 200?
5. F12 → Console → красные строки

**Частые причины:**
- CSP блокирует (90% случаев) → добавить домен в `connect-src`
- 502 от tileserver → перезапустить контейнер
- 0 байт от тайлов → проверить mbtiles содержит данные для нужного z/x/y
- Подписей нет → глифы не загрузились, проверить /fonts/

**Файлы для правки (если что-то реально сломано):**
- `deploy/nginx/proxy.conf` — прокси, CSP, locations
- `frontend/public/maps/positron-style.json` — стиль карты
- `frontend/.env` — какой стиль использовать

---

*Создано: 2026-07-27, hr-orchestrator*
*Обновлять: при изменении архитектуры карты, добавлении новых сервисов*
