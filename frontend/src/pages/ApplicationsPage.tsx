import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { applicationsApi } from "@/api/applications";
import { extractApiError } from "@/api/client";
import Button from "@/components/Button";
import { cn } from "@/utils/cn";
import type { Application, ApplicationStatus } from "@/types";

const STATUS_CONFIG: Record<
  ApplicationStatus,
  { label: string; bg: string; text: string }
> = {
  pending: { label: "На рассмотрении", bg: "bg-blue-100 dark:bg-blue-900/40", text: "text-blue-800 dark:text-blue-200" },
  accepted: { label: "Принято", bg: "bg-green-100 dark:bg-green-900/40", text: "text-green-800 dark:text-green-200" },
  rejected: { label: "Отклонено", bg: "bg-red-100 dark:bg-red-900/40", text: "text-red-800 dark:text-red-200" },
  withdrawn: { label: "Отозвано", bg: "bg-gray-200 dark:bg-gray-700/40", text: "text-gray-600 dark:text-gray-300" },
};

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function StatusBadge({ status }: { status: ApplicationStatus }): JSX.Element {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        cfg.bg,
        cfg.text,
      )}
    >
      {cfg.label}
    </span>
  );
}

export default function ApplicationsPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number(searchParams.get("page")) || 1);

  const [data, setData] = useState<{
    items: Application[];
    total: number;
    page: number;
    page_size: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [withdrawingId, setWithdrawingId] = useState<number | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const res = await applicationsApi.listMy({
          page,
          page_size: 10,
        });
        if (!cancelled) setData(res);
      } catch (err) {
        if (!cancelled) setError(extractApiError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [page]);

  async function handleWithdraw(app: Application): Promise<void> {
    setConfirmId(null);
    setWithdrawingId(app.id);
    try {
      const updated = await applicationsApi.withdraw(app.id);
      setData((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((a) =>
                a.id === app.id ? updated : a,
              ),
            }
          : prev,
      );
    } catch (err) {
      setError(extractApiError(err));
    } finally {
      setWithdrawingId(null);
    }
  }

  function goToPage(p: number): void {
    setSearchParams({ page: String(p) });
  }

  return (
    <div className="page">
      <h1 className="page__title">Мои отклики</h1>

      {error && (
        <div className="mb-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/30 dark:text-red-200">
          {error}
        </div>
      )}

      {loading && (
        <p className="muted py-8 text-center">Загрузка…</p>
      )}

      {!loading && !error && data && data.items.length === 0 && (
        <p className="muted py-8 text-center">
          У вас пока нет откликов.{" "}
          <Link to="/vacancies" className="text-brand-600 hover:underline">
            Перейти к вакансиям
          </Link>
        </p>
      )}

      {!loading && data && data.items.length > 0 && (
        <>
          <div className="space-y-3">
            {data.items.map((app) => (
              <div
                key={app.id}
                className={cn(
                  "card flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between",
                )}
              >
                <div className="min-w-0 flex-1">
                  <Link
                    to={`/vacancies/${app.vacancy_id}`}
                    className="text-base font-semibold text-brand-700 hover:underline dark:text-brand-400"
                  >
                    {app.vacancy_title ?? `Вакансия #${app.vacancy_id}`}
                  </Link>
                  <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs muted">
                    {app.employer_name && (
                      <span>{app.employer_name}</span>
                    )}
                    <span>{formatDate(app.created_at)}</span>
                  </div>
                  {app.cover_letter && (
                    <p className="mt-1 text-sm text-ink-600 dark:text-ink-300 line-clamp-2">
                      {app.cover_letter}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <StatusBadge status={app.status} />
                  {app.status === "pending" && (
                    confirmId === app.id ? (
                      <div className="flex items-center gap-1">
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => handleWithdraw(app)}
                          loading={withdrawingId === app.id}
                        >
                          Да, отозвать
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirmId(null)}
                        >
                          Нет
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setConfirmId(app.id)}
                        loading={withdrawingId === app.id}
                      >
                        Отозвать
                      </Button>
                    )
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Пагинация */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-center gap-1">
              <button
                type="button"
                className="btn-ghost px-3 py-1 text-sm"
                disabled={page <= 1}
                onClick={() => goToPage(page - 1)}
              >
                ← Назад
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  type="button"
                  className={cn(
                    "rounded-lg px-3 py-1 text-sm font-medium transition-colors",
                    p === page
                      ? "bg-brand-600 text-white"
                      : "text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-ink-800",
                  )}
                  onClick={() => goToPage(p)}
                >
                  {p}
                </button>
              ))}
              <button
                type="button"
                className="btn-ghost px-3 py-1 text-sm"
                disabled={page >= totalPages}
                onClick={() => goToPage(page + 1)}
              >
                Вперёд →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
