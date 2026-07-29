import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";
import { readFileSync } from "node:fs";

const API_BASE_URL = process.env.VITE_API_BASE_URL ?? "/api/v1";

// Читаем версию из package.json для версионирования кэша SW
const pkg = JSON.parse(readFileSync(path.resolve(__dirname, "package.json"), "utf-8"));
const APP_VERSION = pkg.version ?? "0.0.0";
const BUILD_DATE = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
const CACHE_TAG = `${APP_VERSION}-${BUILD_DATE}`;

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      disable: false,
      filename: "sw.js",
      // Разрешаем фолбэк для SPA-навигации: при офлайне по любому маршруту отдаём index.html.
      navigateFallback: "/index.html",
      navigateFallbackDenylist: [/^\/api\//, /^\/sw\.js$/, /^\/workbox-/, /\.json$/],
      includeAssets: ["favicon.ico"],
      manifest: {
        name: "JobMap",
        short_name: "JobMap",
        description: "Кроссплатформенный сервис поиска работы и подработки",
        theme_color: "#0f172a",
        background_color: "#0f172a",
        display: "standalone",
        start_url: "/",
        lang: "ru",
        icons: [
          {
            src: "favicon.ico",
            sizes: "64x64 32x32 24x24 16x16",
            type: "image/x-icon",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
        // Управляем кэшем вручную через runtimeCaching — никаких дефолтных precache-переопределений.
        cleanupOutdatedCaches: true,
        // В проде Workbox пишет полезный лог, в dev — нет.
        // eslint-disable-next-line no-console
        ...(process.env.NODE_ENV === "production" ? {} : { suppressWarnings: false }),
        runtimeCaching: [
          // ── 1. index.html / документы — NetworkFirst (всегда свежий) ──
          {
            urlPattern: ({ request }) => request.destination === "document",
            handler: "NetworkFirst",
            options: {
              cacheName: `jobmap-html-${CACHE_TAG}`,
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60, // 1 час
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          // ── 2. Hashed JS/CSS (index-abcdef.js) — CacheFirst (иммутабельные) ──
          {
            urlPattern: ({ url }) => /\/index-[a-f0-9]+\.(js|css)$/.test(url.pathname),
            handler: "CacheFirst",
            options: {
              cacheName: `jobmap-hashed-${CACHE_TAG}`,
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 365, // 1 год — хэш в имени гарантирует уникальность
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          // ── 3. GET /api/vacancies* — network-first с fallback в cache, TTL ~1 час ──
          {
            urlPattern: ({ url, request }) =>
              request.method === "GET" && url.pathname.includes("/api/") && url.pathname.includes("/vacancies"),
            handler: "NetworkFirst",
            options: {
              cacheName: `jobmap-api-vacancies-${CACHE_TAG}`,
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60, // 1 час
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          // ── 4. Прочие GET к /api/* (например, /auth/me) — network-first, без долгого хранения ──
          {
            urlPattern: ({ url, request }) =>
              request.method === "GET" && url.pathname.includes("/api/") && !url.pathname.includes("/vacancies"),
            handler: "NetworkFirst",
            options: {
              cacheName: `jobmap-api-other-${CACHE_TAG}`,
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 60 * 5, // 5 минут
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          // ── 5. POST/PATCH/PUT/DELETE на /api/* — network-only ──
          {
            urlPattern: ({ url, request }) =>
              request.method !== "GET" && url.pathname.includes("/api/"),
            handler: "NetworkOnly",
            options: {
              cacheName: `jobmap-api-mutations-${CACHE_TAG}`,
            },
          },
          // ── 6. Тайлы карты CartoDB — cache-first с expiration ──
          {
            urlPattern: ({ url }) => url.hostname.endsWith("basemaps.cartocdn.com"),
            handler: "CacheFirst",
            options: {
              cacheName: "jobmap-map-tiles",
              expiration: {
                maxEntries: 500,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 дней
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          // ── 7. Прочие статические ассеты (CDN-шрифты, изображения) — stale-while-revalidate ──
          {
            urlPattern: ({ request }) =>
              request.destination === "image" ||
              request.destination === "font" ||
              request.destination === "style",
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: `jobmap-static-assets-${CACHE_TAG}`,
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 60 * 60 * 24 * 7,
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    target: "es2022",
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          maplibre: ["maplibre-gl"],
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
  define: {
    __API_BASE_URL__: JSON.stringify(API_BASE_URL),
  },
});
