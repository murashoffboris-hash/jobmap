import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles/global.css";
import { initTheme } from "@/store/theme";

// Применяем тему до первого рендера, чтобы избежать вспышки неверной темы.
initTheme();

const rootEl = document.getElementById("root");
if (!rootEl) {
  throw new Error("Root element #root not found");
}

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);

// Регистрация service worker — vite-plugin-pwa подхватывает автоматически,
// но добавляем явный fallback на /sw.js на случай отключённого PWA-плагина.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .catch((err) => console.warn("[JobMap] SW fallback register failed:", err));
  });
}
