# JobMap Frontend

Кроссплатформенный клиент **JobMap** (React + TypeScript + Vite + Capacitor + PWA + MapLibre).

## Стек

- **React 18** + **TypeScript** (strict mode) + **Vite**
- **React Router** v6 для маршрутизации
- **Zustand** для состояния (auth-store)
- **Axios** для API (`baseURL` из `VITE_API_BASE_URL`)
- **MapLibre GL JS** для карты
- **vite-plugin-pwa** + fallback `/public/sw.js` — офлайн-оболочка
- **Capacitor** — бандлинг для iOS/Android (`webDir: dist`)

## Структура

```
frontend/
├── public/
│   ├── manifest.json
│   ├── sw.js
│   └── favicon.ico
├── src/
│   ├── components/      # Navbar, MapContainer, VacancyCard
│   ├── pages/           # HomePage, LoginPage, RegisterPage, VacancyListPage, VacancyDetailPage, NotFoundPage
│   ├── api/             # client.ts (axios), auth.ts, vacancies.ts
│   ├── store/           # zustand: auth.ts
│   ├── hooks/           # useAuth.ts
│   ├── types/           # доменные типы (User, Vacancy, ...)
│   ├── utils/           # format.ts (з/п, тип занятости, парсинг env)
│   ├── styles/global.css
│   ├── App.tsx
│   ├── main.tsx
│   └── vite-env.d.ts
├── index.html
├── vite.config.ts
├── capacitor.config.ts
├── tsconfig.json
├── tsconfig.node.json
├── package.json
└── .env.example
```

## Команды

```bash
# Установка
npm install

# Локальная разработка (http://localhost:5173, прокси /api → http://localhost:8001)
npm run dev

# Прод-сборка в dist/
npm run build

# Проверка статической типизации
npm run lint

# Capacitor (после npm run build)
npx cap add ios        # один раз
npx cap add android    # один раз
npx cap sync           # копирует dist/ в нативные проекты
npx cap open ios       # открывает Xcode
npx cap open android   # открывает Android Studio
```

## Переменные окружения

См. `.env.example`:

| Переменная | Назначение |
|---|---|
| `VITE_API_BASE_URL` | Базовый URL API (по умолчанию `/api/v1`) |
| `VITE_MAP_STYLE_URL` | URL стиля MapLibre (по умолчанию `https://demotiles.maplibre.org/style.json`) |
| `VITE_MAP_DEFAULT_CENTER` | `[lng,lat]` для стартового центра карты (Минск) |
| `VITE_MAP_DEFAULT_ZOOM` | начальный zoom |

## Acceptance

- `npm install && npm run dev` — стартует без ошибок
- `npm run build` — успешная TS-сборка + Vite-бандл в `dist/`
- `dist/manifest.json` присутствует (PWA)
- `dist/sw.js` регистрируется автоматически
- `dist/assets/` содержит чанк `maplibre-*.js`
- `dist/index.html` ссылается на собранный JS/CSS
