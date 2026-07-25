/**
 * Регистрация service worker + управление обновлениями PWA.
 *
 * vite-plugin-pwa встраивает виртуальный модуль `virtual:pwa-register`,
 * который генерирует хелпер `registerSW` — он подписывается на событие
 * `onNeedRefresh` (новая версия в фоне) и `onOfflineReady` (SW готов к офлайну).
 *
 * Дополнительно мы ставим простую систему событий, чтобы React-компоненты
 * могли подписаться на "доступна новая версия" и показать промпт "обновить?".
 */

import { registerSW as registerSWVirtual } from "virtual:pwa-register";

export type ReloadPromptEvent = { type: "needRefresh" | "offlineReady" };

type Listener = () => void;

const listeners = new Set<Listener>();
let currentEvent: ReloadPromptEvent | null = null;

function emit(event: ReloadPromptEvent): void {
  currentEvent = event;
  listeners.forEach((l) => {
    try {
      l();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("[JobMap/pwa] listener error", err);
    }
  });
}

/**
 * Тестовый/управляемый эмиттер. В проде используется только изнутри,
 * но экспорт удобен для unit-тестов, чтобы не возиться с моками
 * `virtual:pwa-register`.
 */
export function __emitPwaEvent(event: ReloadPromptEvent): void {
  emit(event);
}

export function subscribeToSW(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getCurrentSWEvent(): ReloadPromptEvent | null {
  return currentEvent;
}

export function clearSWEvent(): void {
  currentEvent = null;
  listeners.forEach((l) => {
    try {
      l();
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("[JobMap/pwa] listener error", err);
    }
  });
}

/**
 * Регистрирует SW. Возвращает функцию `applyUpdate`, которую UI вызывает,
 * когда пользователь соглашается на обновление.
 */
export function registerSW(): { applyUpdate: () => Promise<void> } {
  if (typeof window === "undefined") {
    return { applyUpdate: async () => {} };
  }

  // Кастомный апдейтер: копим ссылку и дёргаем её при applyUpdate.
  let pendingUpdate: (reload?: boolean) => Promise<void> = async () => {};

  registerSWVirtual({
    immediate: true,
    onNeedRefresh() {
      emit({ type: "needRefresh" });
    },
    onOfflineReady() {
      emit({ type: "offlineReady" });
    },
    onRegistered(_registration: ServiceWorkerRegistration | undefined) {
      // Можно подвязать логгирование в dev. Молчим.
    },
    onRegisterError(err: unknown) {
      // eslint-disable-next-line no-console
      console.warn("[JobMap/pwa] SW register error:", err);
    },
  });

  return {
    async applyUpdate() {
      try {
        await pendingUpdate(true);
      } finally {
        // Полный релоад после применения новой версии — иначе пользователь
        // продолжит работать на старом кэше.
        window.location.reload();
      }
    },
  };
}
