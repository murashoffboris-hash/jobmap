import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { vacanciesApi } from "@/api/vacancies";
import { extractApiError } from "@/api/client";
import { formatEmploymentType, formatSalary } from "@/utils/format";
import type { Vacancy } from "@/types";

export default function VacancyDetailPage(): JSX.Element {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      </div>
    </div>
  );
}
