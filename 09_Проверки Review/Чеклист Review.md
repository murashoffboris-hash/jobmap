# Чеклист Review

## Backend (Python/FastAPI)

### Код
- [ ] Соответствие спецификации
- [ ] Соответствие архитектуре
- [ ] Type hints обязательны
- [ ] Docstrings для публичных функций
- [ ] Async/await правильно использованы
- [ ] Обработка ошибок
- [ ] Логирование (если требуется)

### Безопасность
- [ ] SQL injection (parameterized queries)
- [ ] XSS (input sanitization)
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Authentication/Authorization
- [ ] Secrets не в коде

### База данных
- [ ] Миграции корректны
- [ ] Индексы добавлены (если требуется)
- [ ] Foreign keys правильные
- [ ] No N+1 queries
- [ ] Transaction management

### Тесты
- [ ] Unit-тесты написаны
- [ ] Покрытие >= 80%
- [ ] Тесты проходят локально
- [ ] Edge cases покрыты

### Документация
- [ ] API документация обновлена
- [ ] Comments в коде (если требуется)
- [ ] README обновлён (если требуется)

---

## Frontend (TypeScript/React)

### Код
- [ ] Соответствие спецификации
- [ ] Соответствие архитектуре
- [ ] TypeScript strict mode
- [ ] Компоненты функциональные с hooks
- [ ] Обработка ошибок
- [ ] Loading states
- [ ] Error boundaries

### UI/UX
- [ ] Адаптивность (responsive)
- [ ] Доступность (a11y)
- [ ] Keyboard navigation
- [ ] Screen reader support
- [ ] Loading indicators
- [ ] Error messages

### Производительность
- [ ] React.memo для чистых компонентов
- [ ] useMemo/useCallback (если требуется)
- [ ] Lazy loading
- [ ] Code splitting
- [ ] Image optimization

### Тесты
- [ ] Unit-тесты написаны
- [ ] Component-тесты написаны
- [ ] Покрытие >= 80%
- [ ] Тесты проходят локально

### Стилизация
- [ ] CSS Modules или Tailwind
- [ ] No inline styles (кроме динамических)
- [ ] Consistent design system
- [ ] Dark mode support (если требуется)

---

## Git

### Коммиты
- [ ] Формат: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`
- [ ] Язык: русский
- [ ] Atomic commits (один коммит = одна логическая единица)
- [ ] No merge commits (squash preferred)

### Ветки
- [ ] Feature-ветка создана правильно
- [ ] Ветка актуальна (rebase на main)
- [ ] No conflicts

### Pull Request
- [ ] Название PR понятное
- [ ] Описание PR содержит:
  - Что изменено
  - Почему изменено
  - Как тестировать
  - Скриншоты (если UI)
- [ ] Reviewers назначены
- [ ] Labels добавлены
- [ ] Milestone указан (если требуется)

---

## Документация

### Obsidian
- [ ] Паспорт проекта обновлён (если требуется)
- [ ] Архитектура обновлена (если требуется)
- [ ] Требования обновлены (если требуется)
- [ ] Журнал изменений обновлён
- [ ] ADR создан (если архитектурное решение)

### API документация
- [ ] Endpoints задокументированы
- [ ] Request/Response примеры
- [ ] Error codes описаны

---

## Интеграция

### Docker
- [ ] Dockerfile обновлён (если требуется)
- [ ] docker-compose.yml обновлён (если требуется)
- [ ] Environment variables задокументированы

### CI/CD
- [ ] Pipeline проходит
- [ ] Tests проходят
- [ ] Linting проходит

---

## Финальная проверка

- [ ] Все замечания исправлены
- [ ] Code review approved
- [ ] QA passed
- [ ] Documentation updated
- [ ] No TODOs left (или задокументированы)
- [ ] No console.log/debug statements
- [ ] No commented-out code

---

## История проверок

| Дата | Компонент | Результат | Действия |
|------|-----------|-----------|----------|
| 2026-07-24 | Backend: health endpoint | ✅ OK — 5/7 сервисов (nominatim/osrm исключены временно) | Создан t_a67e0bb8 на восстановление после DNS |
| 2026-07-24 | Frontend: стиль карты | ✅ Переключён с demotiles на CartoDB Positron | Города/улицы видны, карта информативна |
| 2026-07-24 | Backend: enum values_callable | ✅ Исправлена сериализация UserRole | Пользователи корректно сохраняются в БД |
| 2026-07-24 | Backend: eager loading | ✅ selectinload для vacancies | N+1 запросов нет |
| 2026-07-24 | Frontend: vitest | ✅ 14 тестов passed (Button, Input, Avatar) | Покрытие компонентов базовое |
| 2026-07-24 | Backend: пагинация | ✅ Пагинация вакансий работает | limit/offset корректны |
| 2026-07-24 | Backend: serialization_alias | ✅ currency → валюта корректна в API | VacancyListItem больше не падает |
| 2026-07-24 | Frontend: профиль | ✅ Страница профиля + редактирование | Пользователь видит/меняет свои данные |
| 2026-07-24 | Frontend: CSS HomePage | ✅ Карта + layout исправлены | Главная страница не разъезжается |
| 2026-07-24 | Infra: Docker | ✅ 7/7 контейнеров запущены | backend/frontend/nginx/redis/worker/minio — все Up |
| 2026-07-24 | Backend: тесты (pytest) | ⚠️ 4 skipped — нет локального PostGIS | Тесты интеграции с БД заскипаны |
| 2026-07-24 | Infra: HTTPS | 🚫 BLOCKED — DNS не настроен | Сертификаты Let's Encrypt ждут DNS (t_210e4524) |
| 2026-07-25 | Docs: MVP-отчёт | ✅ Создан [[11_Релизы/MVP-cycle-1]] | Финальный отчёт по циклу |
| 2026-07-25 | Docs: AGENTS.md | ✅ Обновлён — таблица «куда жаловаться» | 11 ролей → 11 строк эскалации |
| 2026-07-25 | Docs: журнал | ✅ Запись v1.1.0 (2026-07-25) | Итоги MVP, ограничения, блокировки |

---

**Последняя проверка:** 2026-07-25  
**Ревьюер:** hr-documenter (документация)  
**Статус:** ✅ DOCUMENTATION UPDATED — цикл MVP-1 задокументирован
