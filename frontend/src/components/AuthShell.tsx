import { type ReactNode } from "react";
import { motion } from "framer-motion";
import { Sparkles, MapPin, Briefcase } from "lucide-react";

interface AuthShellProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}

/**
 * Общий каркас для страниц аутентификации (login/register).
 * Слева — форма, справа — продающий блок с фичами. На мобильных — только форма.
 * Используется только для UI, без логики.
 */
export default function AuthShell({ title, subtitle, children, footer }: AuthShellProps): JSX.Element {
  return (
    <div className="relative isolate min-h-[calc(100vh-4rem)] overflow-hidden bg-auth-gradient">
      {/* Декоративные блобы на фоне */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 -left-32 h-72 w-72 rounded-full bg-brand-400/30 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-32 -right-24 h-80 w-80 rounded-full bg-sky-400/20 blur-3xl"
      />

      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl grid-cols-1 items-center gap-10 px-4 py-10 lg:grid-cols-2 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="order-2 lg:order-1"
        >
          <div className="mx-auto w-full max-w-md rounded-2xl border border-ink-200/70 bg-white/80 p-6 shadow-soft backdrop-blur-md sm:p-8 dark:border-ink-800 dark:bg-ink-900/70">
            <h1 className="text-balance text-2xl font-semibold tracking-tight text-ink-900 dark:text-ink-50">
              {title}
            </h1>
            <p className="mt-1.5 text-sm text-ink-500 dark:text-ink-400">{subtitle}</p>

            <div className="mt-6">{children}</div>

            {footer && (
              <div className="mt-6 border-t border-ink-100 pt-4 text-center text-sm dark:border-ink-800">
                {footer}
              </div>
            )}
          </div>
        </motion.div>

        <motion.aside
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.05, ease: "easeOut" }}
          className="order-1 hidden lg:order-2 lg:block"
        >
          <div className="relative">
            <div className="inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white/70 px-3 py-1 text-xs font-medium text-brand-700 shadow-sm dark:border-brand-500/30 dark:bg-ink-900/60 dark:text-brand-300">
              <Sparkles size={14} aria-hidden="true" />
              <span>JobMap · работа рядом</span>
            </div>
            <h2 className="mt-4 text-balance text-4xl font-semibold tracking-tight text-ink-900 dark:text-ink-50">
              Найдите подработку или сотрудника на карте.
            </h2>
            <p className="mt-3 max-w-md text-base text-ink-600 dark:text-ink-300">
              Вакансии с геопривязкой, быстрый отклик и современный чат. Регистрация занимает меньше минуты.
            </p>

            <ul className="mt-6 space-y-3 text-sm text-ink-700 dark:text-ink-200">
              <Feature icon={<MapPin size={16} />} title="Вакансии на карте" desc="Видьте предложения рядом с вами — без скролла ленты." />
              <Feature icon={<Briefcase size={16} />} title="Подработка и полный день" desc="Гибкие форматы занятости под ваш график." />
              <Feature icon={<Sparkles size={16} />} title="Без спама" desc="Только релевантные отклики и прозрачные условия." />
            </ul>
          </div>
        </motion.aside>
      </div>
    </div>
  );
}

function Feature({
  icon,
  title,
  desc,
}: {
  icon: React.ReactNode;
  title: string;
  desc: string;
}): JSX.Element {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-500/15 dark:text-brand-300">
        {icon}
      </span>
      <div>
        <div className="font-medium">{title}</div>
        <div className="muted">{desc}</div>
      </div>
    </li>
  );
}
