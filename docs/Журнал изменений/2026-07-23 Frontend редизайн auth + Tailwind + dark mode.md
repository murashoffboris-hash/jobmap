# Frontend — редизайн auth-страниц и современный UI (Tailwind + framer-motion)

**Дата:** 2026-07-23
**Профиль:** programmer-minimax
**Задача:** Kanban `t_35d52991`
**Ветка:** `infra/initial-audit`

## Что сделано

Полный редизайн клиентской части входа/регистрации и шапки на современный стек:
вместо базовых BEM-классов — **Tailwind CSS 3.4** с кастомной дизайн-системой,
**framer-motion** для плавных переходов, **lucide-react** для иконок.

### Дизайн-система
- Подключён Tailwind CSS (PostCSS + autoprefixer).
- Конфиг `tailwind.config.js`:
  - Кастомная палитра `brand` (фиолетовая, от `#f5f3ff` до `#2e1065`) и `ink` (нейтральные slate).
  - `darkMode: 'class'` — переключение без вмешательства ОС.
  - Тени `soft` / `glow`, фон `auth-gradient`, keyframes `fade-in`, `shimmer`.
- `src/styles/global.css` переписан на `@tailwind base/components/utilities` + `@layer`-компоненты
  (`.btn`, `.btn-primary`, `.input`, `.card`, `.label`, `.muted`, `.chip`, `.glass`).
- Сохранены классы совместимости `.app` / `.app__main` — старые компоненты продолжают работать.

### Стора и утилиты
- `src/store/theme.ts` — Zustand-стор темы + `initTheme()`, вызывается в `main.tsx`
  до первого рендера, чтобы не было вспышки неверной темы.
  Сохраняется в `localStorage` (`jobmap.theme`), fallback на `prefers-color-scheme`.
- `src/utils/cn.ts` — `clsx + tailwind-merge` для безопасного склеивания классов.
- `src/utils/avatar.ts` — `getInitials()` (с поддержкой кириллицы) и детерминированный `getAvatarColor()`.

### UI-примитивы
- `Button.tsx` — `forwardRef`, варианты `primary | outline | ghost`, размеры, `loading`-спиннер,
  `leftIcon`/`rightIcon`, `fullWidth`. Default `type="button"`, чтобы случайный Enter в форме
  не сабмитил.
- `Input.tsx` — поле с label, `leftIcon`, `rightSlot`, валидационным `error`/hint и aria-invalid.
- `Avatar.tsx` — круглый аватар с градиентом и инициалами, размеры xs/sm/md/lg.
- `AuthShell.tsx` — общий каркас auth-страниц: glass-карточка слева, продающий блок справа
  (только на десктопе), декоративные блобы на фоне, framer-motion появление.

### Header (заменил старый Navbar)
- Sticky-прозрачный хедер с backdrop-blur, brand-логотипом JobMap + Sparkles-иконкой.
- Адаптив: на мобильных — гамбургер → выезжающая справа шторка (framer-motion spring).
- Theme toggle (Sun/Moon) с правильным `aria-label`.
- Для гостя: кнопки «Войти» / «Регистрация».
- Для залогиненного: avatar + имя → выпадающее меню (Профиль / Мои вакансии / Выйти).
  Закрывается по клику вне и по Escape.
- Роль пользователя показывается chip-ом (`Соискатель` / `Работодатель` / `Администратор`).

### ProtectedRoute
- `src/components/ProtectedRoute.tsx` — обёртка над роутами.
- Без токена → редирект на `/login` с сохранением `from` в location.state.
- С токеном — bootstrap через `authApi.me()`; пока идёт запрос, показывается спиннер.
- При ошибке bootstrap — редирект на логин.

### LoginPage
- Поля email/пароль, иконки lucide слева, `Input`-компонент с показом ошибок под полем.
- Валидация: email по regex, пароль ≥ 6.
- Серверные ошибки (401/404) собираются в общий баннер под формой.
- `framer-motion`: плавное появление формы, fade-in баннера ошибки.
- Логотип JobMap → «С возвращением 👋», подзаголовок с CTA.
- На десктопе — продающий блок справа (фичи: «Вакансии на карте», «Подработка и полный день», «Без спама»).
- После успешного входа — редирект на `state.from` (или `/`).

### RegisterPage
- Поля: имя, email, пароль, повтор пароля, выбор роли.
- Выбор роли — **две большие плитки** (`worker` / `employer`) с иконкой, заголовком и подсказкой.
  Активная плитка подсвечена brand-цветом и `shadow-glow`.
- Валидация: имя ≥ 2 символа, email-формат, пароль ≥ 6, совпадение паролей.
- Серверные ошибки (например, «email занят») выводятся баннером.
- После успешной регистрации — авто-логин (через сторе) → редирект на `/`.

### Прочее
- `main.tsx` вызывает `initTheme()` до `createRoot`.
- `App.tsx` использует новый `Header` вместо `Navbar` и оборачивает
  `/vacancies/:id` в `ProtectedRoute` (пример защищённого маршрута).
- Удалён старый `components/Navbar.tsx`.
- `tsconfig.json` отделён от build-конфигов (теперь в `tsconfig.node.json`).
- `tsconfig.node.json` включает `tailwind.config.js` и `postcss.config.js` для typecheck.

## Установленные зависимости

```
+ tailwindcss@3.4.13         (dev)
+ postcss@8.4.47             (dev)
+ autoprefixer@10.4.20       (dev)
+ framer-motion@11.5.4
+ lucide-react@0.451.0
+ clsx@2.1.1
+ tailwind-merge@2.5.2
+ @types/node                (dev, было)
```

## Проверки

- `npx tsc --noEmit` — 0 ошибок.
- `npm run build` (`tsc -b && vite build`) — успешно за 5.4 с, без warnings:
  - `dist/assets/index-*.css` 98.4 kB (gzip 14.7 kB)
  - `dist/assets/index-*.js`  223 kB (gzip 75 kB)
  - `dist/assets/maplibre-*.js` 801 kB (gzip 217 kB) — отдельный чанк
- `npm run dev` (порт 5174) — отдаёт 200 на `/`, `/login`, `/register`,
  исходники `/src/main.tsx` и `/src/styles/global.css` подгружаются.
- Визуальная проверка в браузере (светлая + тёмная темы) — вёрстка корректна,
  Tailwind-классы применены, glass-карточки, градиенты, плавные переходы работают.

## Acceptance (по ТЗ)

| Требование | Статус |
|---|---|
| LoginPage: email + password + «Войти» + ссылка на регистрацию | ✅ |
| JWT в localStorage | ✅ (через api/client + auth store) |
| Редирект после логина | ✅ (на `state.from` или `/`) |
| Обработка ошибок входа | ✅ (валидация полей + баннер серверной ошибки) |
| RegisterPage: все поля + валидация | ✅ (включая совпадение паролей и email-формат) |
| Авто-логин после регистрации | ✅ (в сторе register вызывает login) |
| Обработка ошибок регистрации | ✅ |
| Header: лого слева, гость → «Войти/Регистрация», залогинен → аватар+меню | ✅ |
| Адаптив мобил/десктоп | ✅ (гамбургер-шторка на мобильных) |
| Дизайн: современный, фиолетовый акцент, плавные анимации | ✅ (Tailwind + framer-motion) |
| Тёмная тема (toggle) | ✅ |
| Круглые аватары с инициалами | ✅ |
| ProtectedRoute | ✅ |
| axios-интерсептор (Bearer + 401) | ✅ (уже было в предыдущей задаче) |
| `npm run dev` без ошибок TS/линтера | ✅ |

## Изменённые файлы

```
frontend/package.json
frontend/package-lock.json
frontend/postcss.config.js          (new)
frontend/tailwind.config.js         (new)
frontend/tsconfig.json
frontend/tsconfig.node.json
frontend/src/App.tsx
frontend/src/main.tsx
frontend/src/styles/global.css
frontend/src/pages/LoginPage.tsx
frontend/src/pages/RegisterPage.tsx
frontend/src/components/Header.tsx           (new)
frontend/src/components/AuthShell.tsx        (new)
frontend/src/components/Avatar.tsx           (new)
frontend/src/components/Button.tsx           (new)
frontend/src/components/Input.tsx            (new)
frontend/src/components/ProtectedRoute.tsx   (new)
frontend/src/components/Navbar.tsx           (deleted)
frontend/src/store/theme.ts                  (new)
frontend/src/utils/cn.ts                     (new)
frontend/src/utils/avatar.ts                 (new)
```

## Дальнейшие шаги (для следующих задач)

- Добавить страницу `/profile` (Header уже ссылается на неё).
- Сделать страницу «Мои вакансии» (`/vacancies?mine=1`) с фильтрацией по владельцу.
- Реализовать восстановление пароля (новый AuthShell подойдёт как каркас).
- Backend: подтвердить, что `POST /api/v1/auth/register` для роли `worker` действительно
  возвращает пользователя и не падает на дубликате email с 409.
