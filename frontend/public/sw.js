// JobMap — Service Worker (fallback для PWA)
// vite-plugin-pwa генерирует основной SW через Workbox; этот файл —
// явный fallback на случай, если PWA-плагин ещё не отработал.
const CACHE = "jobmap-shell-v1";
const CORE = ["/", "/index.html", "/manifest.json", "/favicon.ico"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  // Не кэшируем API — там бэкенд с авторизацией.
  const url = new URL(req.url);
  if (url.pathname.startsWith("/api/")) return;

  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((res) => {
          if (res.ok && (req.destination === "document" || req.destination === "script" || req.destination === "style")) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => caches.match("/index.html"));
    }),
  );
});
