import { useEffect, useState } from "react";

/**
 * Возвращает текущее состояние сети.
 * Инициализируется из `navigator.onLine`, далее обновляется через
 * `online` / `offline` события на `window`.
 *
 * ВАЖНО: `navigator.onLine` в браузерах сообщает "есть соединение с сетью",
 * но не гарантирует реальный доступ к интернету. Используем его как
 * быстрый сигнал для UI; для фактической проверки бэкенд отвечает 4xx/5xx.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState<boolean>(() => {
    if (typeof navigator === "undefined") return true;
    return navigator.onLine;
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleOnline = (): void => setOnline(true);
    const handleOffline = (): void => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return online;
}
