import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import MapContainer from "@/components/MapContainer";
import VacancyCard from "@/components/VacancyCard";
import { vacanciesApi } from "@/api/vacancies";
import { formatSalary } from "@/utils/format";
import type { Vacancy, MapPoint } from "@/types";

export default function HomePage(): JSX.Element {
  const navigate = useNavigate();
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await vacanciesApi.list({ page_size: 20 });
        if (!cancelled) setVacancies(res.items);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить вакансии");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const points: MapPoint[] = vacancies
    .filter((v) => v.latitude != null && v.longitude != null)
    .map((v) => ({
      id: v.id,
      lat: v.latitude as number,
      lng: v.longitude as number,
      title: v.title,
      salary: formatSalary(v.salary_from, v.salary_to, v.currency),
      payload: { vacancyId: v.id },
    }));

  return (
    <div className="page">
      <h1 className="page__title">Вакансии на карте</h1>
      <div className="layout">
        <div>
          <MapContainer
            points={points}
            onMarkerClick={(p) => navigate(`/vacancies/${p.id}`)}
          />
        </div>
        <aside>
          {loading && <p className="muted">Загрузка вакансий…</p>}
          {error && <p className="form__error">{error}</p>}
          {!loading && !error && vacancies.length === 0 && (
            <p className="muted">Пока нет вакансий с координатами.</p>
          )}
          {vacancies.slice(0, 10).map((v) => (
            <VacancyCard key={v.id} vacancy={v} />
          ))}
        </aside>
      </div>
    </div>
  );
}
