import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";

const API_BASE_URL = process.env.VITE_API_BASE_URL ?? "/api/v1";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      disable: true, // SW TEMPORARILY DISABLED — кэш браузера не получает обновлённый CSP, MapLibre worker блокируется. Вернуть после PWA v2.
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
          {
            // GET /api/vacancies* — network-first с fallback в cache, TTL ~1 час.
            urlPattern: ({ url, request }) =>
              request.method === "GET" && url.pathname.includes("/api/") && url.pathname.includes("/vacancies"),
            handler: "NetworkFirst",
            options: {
              cacheName: "jobmap-api-vacancies",
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60, // 1 час
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // Прочие GET к /api/* (например, /auth/me) — network-first, без долгого хранения.
            urlPattern: ({ url, request }) =>
              request.method === "GET" && url.pathname.includes("/api/") && !url.pathname.includes("/vacancies"),
            handler: "NetworkFirst",
            options: {
              cacheName: "jobmap-api-other",
              networkTimeoutSeconds: 5,
              expiration: {
                maxEntries: 30,
                maxAgeSeconds: 60 * 5, // 5 минут
              },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            // POST/PATCH/PUT/DELETE на /api/* — network-only (никаких устаревших мутаций).
            urlPattern: ({ url, request }) =>
              request.method !== "GET" && url.pathname.includes("/api/"),
            handler: "NetworkOnly",
            options: {
              cacheName: "jobmap-api-mutations",
            },
          },
          {
            // Тайлы карты CartoDB — cache-first, лимит ~50 MB с expiration.
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
          {
            // Прочие статические ассеты (CDN-шрифты, изображения) — stale-while-revalidate.
            urlPattern: ({ request }) =>
              request.destination === "image" ||
              request.destination === "font" ||
              request.destination === "style",
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "jobmap-static-assets",
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
