import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PlusCircle } from "lucide-react";
import { vacanciesApi } from "@/api/vacancies";
import VacancyCard from "@/components/VacancyCard";
import { extractApiError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { Vacancy } from "@/types";

export default function VacancyListPage(): JSX.Element {
  const [items, setItems] = useState<Vacancy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [city, setCity] = useState("");
  const user = useAuthStore((s) => s.user);
  const isEmployer = user?.role === "employer" || user?.role === "admin";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await vacanciesApi.list({
          page_size: 50,
          search: search.trim() || undefined,
          city: city.trim() || undefined,
        });
        if (!cancelled) setItems(res.items);
      } catch (err) {
        if (!cancelled) setError(extractApiError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [search, city]);

  return (
    <div className="page">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h1 className="text-2xl font-bold text-ink-900 dark:text-ink-50">Вакансии</h1>
        {isEmployer && (
          <Link
            to="/vacancies/new"
            className="btn-primary inline-flex items-center gap-2"
          >
            <PlusCircle size={16} aria-hidden="true" />
            <span>Создать вакансию</span>
          </Link>
        )}
        {!isEmployer && user && (
          <span
            className="chip cursor-not-allowed opacity-60"
            title="Только для работодателей"
          >
            Создание вакансий — только для работодателей
          </span>
        )}
      </div>
      <div className="form" style={{ maxWidth: "unset", marginBottom: "1rem" }}>
        <label className="form__label">
          Поиск
          <input
            className="input"
            placeholder="Должность, ключевые слова…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="form__label">
          Город
          <input
            className="input"
            placeholder="Например, Минск"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />
        </label>
      </div>
      {loading && <p className="muted">Загрузка…</p>}
      {error && <p className="form__error">{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="muted">Ничего не найдено. Попробуйте изменить фильтры.</p>
      )}
      {items.map((v) => (
        <VacancyCard key={v.id} vacancy={v} />
      ))}
    </div>
  );
}
