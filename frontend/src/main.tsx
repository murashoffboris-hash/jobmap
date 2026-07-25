import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles/global.css";
import { initTheme } from "@/store/theme";
import { registerSW } from "@/pwa";

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

// Регистрация service worker через vite-plugin-pwa (Workbox).
// В DEV-режиме виртуальный модуль возвращает no-op — здесь вызов безвреден,
// но оборачиваем в проверку `window`, чтобы код был совместим с SSR-окружением.
if (typeof window !== "undefined") {
  registerSW();
}
