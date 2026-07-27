import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { vacanciesApi } from "@/api/vacancies";
import { applicationsApi } from "@/api/applications";
import { extractApiError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { formatEmploymentType, formatSalary } from "@/utils/format";
import { cn } from "@/utils/cn";
import Button from "@/components/Button";
import type { Vacancy, Application, ApplicationStatus } from "@/types";

const STATUS_CONFIG: Record<
  ApplicationStatus,
  { label: string; bg: string; text: string }
> = {
  pending: { label: "На рассмотрении", bg: "bg-blue-100 dark:bg-blue-900/40", text: "text-blue-800 dark:text-blue-200" },
  accepted: { label: "Принято", bg: "bg-green-100 dark:bg-green-900/40", text: "text-green-800 dark:text-green-200" },
  rejected: { label: "Отклонено", bg: "bg-red-100 dark:bg-red-900/40", text: "text-red-800 dark:text-red-200" },
  withdrawn: { label: "Отозвано", bg: "bg-gray-200 dark:bg-gray-700/40", text: "text-gray-600 dark:text-gray-300" },
};

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

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function VacancyDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const user = useAuthStore((s) => s.user);

  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Apply state
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [coverLetter, setCoverLetter] = useState("");
  const [applying, setApplying] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);

  // Employer: applications for this vacancy
  const [employerApps, setEmployerApps] = useState<Application[]>([]);
  const [employerAppsLoading, setEmployerAppsLoading] = useState(false);
  const [statusUpdatingId, setStatusUpdatingId] = useState<number | null>(null);

  const isOwner = user != null && vacancy != null && user.id === vacancy.employer_id;

  useEffect(() => {
    if (!Number.isFinite(id) || id <= 0) {
      setError("Некорректный идентификатор вакансии");
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const v = await vacanciesApi.get(id);
        if (!cancelled) setVacancy(v);
      } catch (err) {
        if (!cancelled) setError(extractApiError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Load employer's applications
  useEffect(() => {
    if (!isOwner || !vacancy) return;
    let cancelled = false;
    setEmployerAppsLoading(true);
    (async () => {
      try {
        const res = await applicationsApi.listByVacancy(vacancy.id, {
          page_size: 50,
        });
        if (!cancelled) setEmployerApps(res.items);
      } catch {
        // silently fail for this section
      } finally {
        if (!cancelled) setEmployerAppsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isOwner, vacancy?.id]);

  async function handleApply(): Promise<void> {
    setApplyError(null);
    setApplying(true);
    try {
      await applicationsApi.create({
        vacancy_id: id,
        cover_letter: coverLetter.trim() || undefined,
      });
      setApplySuccess(true);
    } catch (err) {
      setApplyError(extractApiError(err));
    } finally {
      setApplying(false);
    }
  }

  async function handleStatusChange(appId: number, status: "accepted" | "rejected"): Promise<void> {
    setStatusUpdatingId(appId);
    try {
      const updated = await applicationsApi.updateStatus(appId, { status });
      setEmployerApps((prev) =>
        prev.map((a) => (a.id === appId ? updated : a)),
      );
    } catch (err) {
      setError(extractApiError(err));
    } finally {
      setStatusUpdatingId(null);
    }
  }

  if (loading) return <p className="page muted">Загрузка…</p>;
  if (error) return <p className="page form__error">{error}</p>;
  if (!vacancy) return <p className="page muted">Вакансия не найдена.</p>;

  return (
    <div className="page">
      <Link to="/vacancies" className="muted">
        ← Все вакансии
      </Link>
      <h1 className="page__title">{vacancy.title}</h1>
      <div className="card">
        <p className="vacancy-meta">
          {vacancy.employer_name ?? "Работодатель"} · {vacancy.city ?? "город не указан"}
        </p>
        <p>
          <strong>{formatSalary(vacancy.salary_from, vacancy.salary_to, vacancy.currency)}</strong> ·{" "}
          {formatEmploymentType(vacancy.employment_type)}
        </p>
        <p style={{ whiteSpace: "pre-wrap" }}>{vacancy.description}</p>

        {/* Кнопка «Откликнуться» — только авторизованным, не владельцу */}
        {user && !isOwner && (
          <div className="mt-4 border-t pt-4">
            {applySuccess ? (
              <p className="text-sm font-medium text-green-700 dark:text-green-400">
                ✓ Вы откликнулись на эту вакансию
              </p>
            ) : (
              <Button onClick={() => setShowApplyModal(true)}>
                Откликнуться
              </Button>
            )}
          </div>
        )}

        {!user && (
          <div className="mt-4 border-t pt-4">
            <p className="text-sm muted">
              <Link to="/login" className="text-brand-600 hover:underline">
                Войдите
              </Link>{" "}
              или{" "}
              <Link to="/register" className="text-brand-600 hover:underline">
                зарегистрируйтесь
              </Link>
              , чтобы откликнуться.
            </p>
          </div>
        )}
      </div>

      {/* Секция работодателя: отклики на вакансию */}
      {isOwner && (
        <section className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Отклики на вакансию</h2>

          {employerAppsLoading && (
            <p className="muted text-sm">Загрузка…</p>
          )}

          {!employerAppsLoading && employerApps.length === 0 && (
            <p className="muted text-sm">Пока нет откликов.</p>
          )}

          {!employerAppsLoading && employerApps.length > 0 && (
            <div className="space-y-3">
              {employerApps.map((app) => (
                <div
                  key={app.id}
                  className="card flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm">
                      {app.applicant_name ?? `Пользователь #${app.user_id}`}
                    </div>
                    {app.cover_letter && (
                      <p className="mt-1 text-sm text-ink-600 dark:text-ink-300 line-clamp-2">
                        {app.cover_letter}
                      </p>
                    )}
                    <div className="mt-1 flex items-center gap-2">
                      <StatusBadge status={app.status} />
                      <span className="text-xs muted">{formatDate(app.created_at)}</span>
                    </div>
                  </div>

                  {app.status === "pending" && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleStatusChange(app.id, "accepted")}
                        loading={statusUpdatingId === app.id}
                      >
                        Принять
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleStatusChange(app.id, "rejected")}
                        loading={statusUpdatingId === app.id}
                      >
                        Отклонить
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Модалка отклика */}
      {showApplyModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 backdrop-blur-sm p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowApplyModal(false);
          }}
        >
          <div className="w-full max-w-md rounded-xl border border-ink-200 bg-white p-6 shadow-xl dark:border-ink-800 dark:bg-ink-900">
            <h3 className="text-lg font-semibold">Отклик на вакансию</h3>
            <p className="mt-1 text-sm muted">{vacancy.title}</p>

            {applyError && (
              <div className="mt-3 rounded-lg border border-red-300 bg-red-50 p-2 text-sm text-red-800 dark:border-red-800 dark:bg-red-900/30 dark:text-red-200">
                {applyError}
              </div>
            )}

            <div className="mt-4">
              <label className="mb-1 block text-sm font-medium">
                Сопроводительное письмо (необязательно)
              </label>
              <textarea
                className="input w-full"
                rows={4}
                maxLength={2000}
                value={coverLetter}
                onChange={(e) => setCoverLetter(e.target.value)}
                placeholder="Расскажите о себе и почему вы подходите на эту вакансию…"
              />
              <p className="mt-1 text-xs muted">
                {coverLetter.length}/2000
              </p>
            </div>

            <div className="mt-4 flex items-center justify-end gap-2">
              <Button
                variant="ghost"
                onClick={() => setShowApplyModal(false)}
              >
                Отмена
              </Button>
              <Button onClick={handleApply} loading={applying}>
                Отправить
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
