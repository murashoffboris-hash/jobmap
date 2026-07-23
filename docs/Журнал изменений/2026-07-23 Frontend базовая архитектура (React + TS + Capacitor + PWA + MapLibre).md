# 2026-07-23 — Frontend: базовая архитектура

## Что сделано

С нуля развёрнут клиент **JobMap** в `D:\Obsidian\HR\frontend\` на стеке
React + TypeScript + Vite + Capacitor + PWA + MapLibre.

### Структура
```
frontend/
├── public/
│   ├── manifest.json            # PWA manifest (name, theme, icons, shortcuts)
│   ├── sw.js                    # Service worker fallback (precache + offline shell)
│   └── favicon.ico              # уже был от предыдущей задачи t_644c680c
├── src/
│   ├── components/              # Navbar, MapContainer, VacancyCard
│   ├── pages/                   # Home, Login, Register, VacancyList, VacancyDetail, NotFound
│   ├── api/                     # client.ts (axios + interceptors), auth.ts, vacancies.ts
│   ├── store/auth.ts            # zustand-стор (login/register/logout/bootstrap)
│   ├── hooks/useAuth.ts         # bootstrap-эффект
│   ├── types/index.ts           # User, AuthTokens, Vacancy, MapPoint, ApiError
│   ├── utils/format.ts          # з/п, тип занятости, парсинг env-центра карты
│   ├── styles/global.css        # дизайн-токены, layout, формы, map-container
│   ├── App.tsx                  # router + routes
│   ├── main.tsx                 # React root + SW register
│   └── vite-env.d.ts            # типы import.meta.env
├── index.html                   # viewport, theme-color, manifest link
├── vite.config.ts               # Vite + React + VitePWA + dev-proxy
├── capacitor.config.ts          # appId, splash, status-bar
├── tsconfig.json                # strict, @ alias, src
├── tsconfig.node.json           # отдельный для vite.config.ts / capacitor.config.ts
├── package.json
├── .env.example
├── .gitignore
└── README.md
```

### Стек
- React 18.3 + TypeScript 5.6 (strict mode, noUnusedLocals, noImplicitOverride)
- Vite 5.4 + @vitejs/plugin-react 4.3
- vite-plugin-pwa 0.20 (Workbox: precache 9 записей, ~1 МБ)
- maplibre-gl 4.7 (вынесен в отдельный Vite-чанк)
- zustand 4.5 + react-router-dom 6.27
- axios 1.7 с interceptor'ом для JWT и авто-чисткой на 401
- @capacitor/core 6.1 + ios/android 6.1 (только конфиг, нативные проекты через `npx cap add ios|android`)

### Acceptance
- `npm install` → 391 пакет установлен, vite/tsc/cap в `node_modules/.bin`
- `npm run build` → `tsc -b` (0 ошибок) + `vite build` (117 модулей, 3.05s)
- `dist/` артефакты:
  - `index.html` (0.91 kB)
  - `assets/index-*.js` (64 kB, gzip 24 kB)
  - `assets/react-*.js` (164 kB, gzip 53 kB)
  - `assets/maplibre-*.js` (801 kB, gzip 218 kB)
  - `assets/index-*.css` (68 kB, gzip 10 kB)
  - `manifest.webmanifest` (PWA)
  - `sw.js` + `workbox-*.js` (PWA runtime)
  - `registerSW.js`
- `npx vite` dev-сервер на :5173 → HTTP 200 на:
  - `/` (root index.html)
  - `/manifest.json` (PWA)
  - `/sw.js` (Service Worker fallback)
  - `/favicon.ico`
  - `/src/main.tsx`, `/src/App.tsx`, `/src/components/MapContainer.tsx` (HMR endpoints)

### Карта
- `MapContainer` — тонкая React-обёртка над MapLibre GL:
  - создаёт инстанс один раз через `useRef`,
  - перерисовывает маркеры при изменении `points` (без пересоздания map),
  - `NavigationControl` + `ScaleControl`,
  - `fitBounds` по всем точкам с padding,
  - `popup` c HTML-escaped title,
  - `onMarkerClick` callback наружу.
- `HomePage` использует `vacanciesApi.list()`, фильтрует вакансии с координатами
  и визуализирует на карте + список в боковой колонке.

### Авторизация
- `useAuthStore` (zustand): `status`, `user`, `error`, `bootstrap()`, `login()`,
  `register()`, `logout()`, `clearError()`.
- JWT хранится в `localStorage` под ключом `jobmap.auth.access`.
- На 401 axios-interceptor автоматически чистит токен.
- `useAuthBootstrap` дёргается из `<Navbar>` для восстановления сессии при старте.

### Capacitor
- `webDir: "dist"` — после `npm run build` достаточно `npx cap sync`.
- Включены `SplashScreen` (тёмный фон, спиннер) и `StatusBar`.

## Подводные камни, которые пришлось решить
1. `tsc -b` со включённым `composite` в `tsconfig.node.json` генерировал
   `vite.config.{js,d.ts}` рядом с `.ts` исходниками — это сбивало Vite с толку
   (Vite приоритетно грузит `.js`). Решение: убрать `composite: true` и
   `noEmit: true` оставить для обоих tsconfig, `.js`/`.d.ts` файлы добавить
   в `.gitignore`.
2. `tsconfig.json` сначала включал `vite.config.ts` напрямую — ломался
   `defineConfig` (браузерные типы не подходят для node-конфига). Решение:
   вынести config'и в отдельный `tsconfig.node.json` с `lib: ["ES2022"]` и
   `types: ["node"]`, в основном `tsconfig.json` оставить только `src/`.
3. Vite-плагин PWA добавил `vite.config.ts` фолбэк `test`-блок (артефакт более
   ранней версии) — удалён, в `package.json` vitest не подключал.

## Следующие шаги
- Подключить реальный backend Auth API (проверить контракты `/auth/login`,
  `/auth/me`, `/auth/register` против `backend/app/routers/auth.py`).
- Перевести `MapContainer` на кластеризацию (supercluster) при >100 точек.
- Добавить e2e-тесты (Vitest + @testing-library/react).
- Кастомизировать PWA-иконки 192/512 (сейчас только favicon.ico).
- Сгенерировать нативные проекты: `npx cap add ios` / `npx cap add android`.
