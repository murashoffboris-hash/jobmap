# Изменение: добавлен favicon JobMap

Дата: 2026-07-23
Git-ветка: infra/initial-audit
Kanban: t_644c680c

## Что изменено
- Добавлен ICO-файл favicon в `frontend/public/favicon.ico`.
- Скопирована собранная статика в `frontend/dist/favicon.ico` для текущего nginx-деплоя.
- Nginx-конфигурация уже обслуживает `.ico` как статический ресурс с кешированием; отдельный `location = /favicon.ico` не требуется.

## Проверка
- `file frontend/public/favicon.ico frontend/dist/favicon.ico` подтверждает Windows icon resource с изображениями 16x16 и 32x32.
- Docker Compose монтирует `frontend/dist` в `/usr/share/nginx/html`, поэтому `/favicon.ico` должен возвращать 200 после перезапуска/обновления контейнера.
