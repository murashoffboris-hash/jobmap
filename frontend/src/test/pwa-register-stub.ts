// Заглушка для virtual:pwa-register в vitest-окружении.
// В рантайме модуль предоставляется Vite-плагином; в тестах возвращаем no-op.
export function registerSW(): (reloadPage?: boolean) => Promise<void> {
  return async () => {};
}
