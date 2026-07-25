import { AnimatePresence, motion } from "framer-motion";
import { WifiOff } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

/**
 * Ненавязчивый баннер «нет соединения», который показывается сверху
 * сразу под sticky-хедером. Автоматически скрывается при возвращении
 * в онлайн.
 *
 * Дизайн в текущей системе проекта: subtle, без отдельных CTA.
 */
export default function OfflineBanner(): JSX.Element {
  const online = useOnlineStatus();
  const visible = !online;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="offline-banner"
          role="status"
          aria-live="polite"
          initial={{ y: -8, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -8, opacity: 0 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="sticky top-16 z-30 w-full border-b border-amber-300/60 bg-amber-50/95 text-amber-900 backdrop-blur-sm dark:border-amber-700/50 dark:bg-amber-900/40 dark:text-amber-100"
          data-testid="offline-banner"
        >
          <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 py-2 text-sm sm:px-6">
            <WifiOff size={16} aria-hidden="true" className="shrink-0" />
            <span className="font-medium">Нет соединения</span>
            <span aria-hidden="true">—</span>
            <span className="truncate">показаны сохранённые данные</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
