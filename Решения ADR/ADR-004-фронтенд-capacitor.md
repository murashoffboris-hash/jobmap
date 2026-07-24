# ADR-004: Фронтенд на React + Capacitor (кроссплатформа)

**Статус:** Принято  
**Дата:** 2026-07-23  
**Контекст:** Необходимо разработать клиентское приложение, работающее на Web, iOS и Android, с минимальным дублированием кода.

## Решение
Использовать **React 18 + TypeScript 5** как основу UI, с **Capacitor 6** для нативной обёртки.

### Архитектура
- **React SPA** — основной UI, routing через React Router v6
- **Vite 5** — сборщик, HMR, code splitting
- **Capacitor 6** — нативная обёртка (iOS WebView / Android WebView)
- **PWA** (vite-plugin-pwa) — офлайн-доступ через Service Worker
- **Tailwind CSS 3.4** — стилизация
- **Zustand** — сторы (auth, theme)
- **MapLibre 4** — карты (OpenStreetMap, tile-сервер)

### Структура проекта
```
frontend/
├── public/          # manifest.json, sw.js, favicon
├── src/
│   ├── components/  # UI-примитивы (Button, Input, Avatar, Header)
│   ├── pages/       # Login, Register, Home, VacancyList, VacancyDetail
│   ├── api/         # axios client + endpoints
│   ├── store/       # zustand stores (auth, theme)
│   ├── hooks/       # кастомные хуки
│   ├── types/       # TypeScript типы
│   ├── utils/       # утилиты (cn, avatar)
│   └── styles/      # global.css (Tailwind directives)
├── capacitor.config.ts
├── vite.config.ts
└── tailwind.config.js
```

### Дизайн-система
- Кастомная палитра: brand-violet + ink slate
- Две темы: светлая + тёмная (class-based dark mode)
- Glassmorphism для auth-форм
- Framer Motion для анимаций переходов
- Lucide React для иконок

### Почему не нативные приложения
- **React Native** — rejected: нужно писать отдельный UI для каждой платформы
- **Flutter** — rejected: другой стек, сложная интеграция с React-экосистемой
- **Capacitor** — выбран: SPA работает везде, нативная обёртка даёт доступ к API устройства

## Последствия
- Единая кодовая база для Web, iOS, Android
- PWA даёт установку на телефон без App Store
- Карты через MapLibre — без платных API-ключей
- Возможность постепенного добавления нативных модулей через Capacitor plugins
- При необходимости — миграция отдельных экранов на React Native не требует переписывания всего приложения
