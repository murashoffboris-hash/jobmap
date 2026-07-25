import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { RefreshCw } from "lucide-react";
import Button from "@/components/Button";
import {
  subscribeToSW,
  getCurrentSWEvent,
  clearSWEvent,
  registerSW,
  type ReloadPromptEvent,
} from "@/pwa";

/**
 * Промпт «доступна новая версия — обновить?». Показывается, когда
 * service worker сообщает `onNeedRefresh` (новая версия скачана в фоне).
 * При клике «Обновить» — applyUpdate() + window.location.reload().
 *
 * Сам по себе не зависит от сети; не показывается в одно и то же время
 * с OfflineBanner (но они визуально совместимы).
 */
export default function ReloadPrompt(): JSX.Element | null {
  const [event, setEvent] = useState<ReloadPromptEvent | null>(getCurrentSWEvent());

  useEffect(() => {
    const unsubscribe = subscribeToSW(() => {
      setEvent(getCurrentSWEvent());
    });
    return unsubscribe;
  }, []);

  if (event?.type !== "needRefresh") return null;

  return (
    <AnimatePresence>
      <motion.div
        key="reload-prompt"
        role="alertdialog"
        aria-live="assertive"
        aria-label="Доступна новая версия"
        initial={{ y: -8, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -8, opacity: 0 }}
        transition={{ duration: 0.18, ease: "easeOut" }}
        className="sticky top-16 z-30 w-full border-b border-brand-300/60 bg-brand-50/95 text-brand-900 backdrop-blur-sm dark:border-brand-700/50 dark:bg-brand-900/40 dark:text-brand-100"
        data-testid="reload-prompt"
      >
        <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2 text-sm sm:px-6">
          <RefreshCw size={16} aria-hidden="true" className="shrink-0" />
          <span className="font-medium">Доступна новая версия</span>
          <span aria-hidden="true">—</span>
          <span className="truncate">обновить сейчас?</span>
          <div className="ml-auto flex items-center gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => clearSWEvent()}
              data-testid="reload-prompt-dismiss"
            >
              Позже
            </Button>
            <Button
              size="sm"
              onClick={async () => {
                const { applyUpdate } = registerSW();
                await applyUpdate();
              }}
              data-testid="reload-prompt-apply"
            >
              Обновить
            </Button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
