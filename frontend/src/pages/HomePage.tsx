import { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import MapContainer from "@/components/MapContainer";
import VacancyCard from "@/components/VacancyCard";
import VacancyFilters, { type VacancyFilterValues } from "@/components/VacancyFilters";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
import { vacanciesApi } from "@/api/vacancies";
import { formatSalary } from "@/utils/format";
import type { Vacancy, MapPoint } from "@/types";

const PAGE_SIZE = 20;

function filtersToParams(f: VacancyFilterValues): Record<string, string> {
  const p: Record<string, string> = {};
  if (f.search) p.search = f.search;
  if (f.city) p.city = f.city;
  if (f.salary_from) p.salary_from = f.salary_from;
  if (f.salary_to) p.salary_to = f.salary_to;
  if (f.schedule_type) p.schedule_type = f.schedule_type;
  return p;
}

function paramsToFilters(sp: URLSearchParams): VacancyFilterValues {
  return {
    search: sp.get("search") ?? "",
    city: sp.get("city") ?? "",
    salary_from: sp.get("salary_from") ?? "",
    salary_to: sp.get("salary_to") ?? "",
    schedule_type: sp.get("schedule_type") ?? "",
  };
}

export default function HomePage(): JSX.Element {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => paramsToFilters(searchParams), [searchParams]);

  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const hasMore = vacancies.length < total;

  // Build API params from filters + page
  const buildParams = useCallback(
    (p: number): Record<string, unknown> => {
      const params: Record<string, unknown> = { page: p, page_size: PAGE_SIZE };
      if (filters.search) params.search = filters.search;
      if (filters.city) params.city = filters.city;
      if (filters.salary_from) params.salary_from = Number(filters.salary_from);
      if (filters.salary_to) params.salary_to = Number(filters.salary_to);
      if (filters.schedule_type) params.schedule_type = filters.schedule_type;
      return params;
    },
    [filters],
  );

  // Initial load / filter change — reset everything
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPage(1);
    setVacancies([]);

    (async () => {
      try {
        const res = await vacanciesApi.list(buildParams(1) as Parameters<typeof vacanciesApi.list>[0]);
        if (!cancelled) {
          setVacancies(res.items);
          setTotal(res.total);
        }
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
  }, [filters, buildParams]);

  // Load more (infinite scroll)
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    const nextPage = page + 1;
    try {
      const res = await vacanciesApi.list(buildParams(nextPage) as Parameters<typeof vacanciesApi.list>[0]);
      setVacancies((prev) => [...prev, ...res.items]);
      setTotal(res.total);
      setPage(nextPage);
    } catch (err) {
      console.warn("Failed to load more vacancies:", err);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMore, page, buildParams]);

  const { sentinelRef } = useInfiniteScroll({
    onLoadMore: loadMore,
    loading: loadingMore,
    hasMore,
  });

  // Update URL when filters change
  const handleFiltersChange = useCallback(
    (newFilters: VacancyFilterValues) => {
      setSearchParams(filtersToParams(newFilters), { replace: true });
    },
    [setSearchParams],
  );

  // Map points — all loaded vacancies with coordinates
  const points: MapPoint[] = useMemo(
    () =>
      vacancies
        .filter((v) => v.latitude != null && v.longitude != null)
        .map((v) => ({
          id: v.id,
          lat: v.latitude as number,
          lng: v.longitude as number,
          title: v.title,
          salary: formatSalary(v.salary_from, v.salary_to, v.currency),
          payload: { vacancyId: v.id },
        })),
    [vacancies],
  );

  return (
    <div className="page">
      <h1 className="page__title">Вакансии на карте</h1>
      <div className="layout">
        {/* Sidebar with filters + vacancy list */}
        <aside className="flex flex-col gap-4">
          <VacancyFilters values={filters} onChange={handleFiltersChange} />

          {loading && <p className="muted">Загрузка вакансий…</p>}
          {error && <p className="form__error">{error}</p>}
          {!loading && !error && vacancies.length === 0 && (
            <p className="muted">Ничего не найдено. Попробуйте изменить фильтры.</p>
          )}

          {vacancies.map((v) => (
            <VacancyCard key={v.id} vacancy={v} />
          ))}

          {/* Infinite scroll sentinel */}
          {hasMore && !loadingMore && <div ref={sentinelRef} data-testid="scroll-sentinel" />}
          {loadingMore && (
            <div className="flex justify-center py-4" data-testid="loading-more">
              <span className="h-6 w-6 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            </div>
          )}
          {!hasMore && vacancies.length > 0 && !loading && (
            <p className="muted text-center text-sm py-2">
              Показано {vacancies.length} из {total} вакансий
            </p>
          )}
        </aside>

        {/* Map */}
        <div>
          <MapContainer points={points} onMarkerClick={(p) => navigate(`/vacancies/${p.id}`)} />
        </div>
      </div>
    </div>
  );
}
