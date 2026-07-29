import { useState, useEffect, useCallback, useRef } from "react";
import { Search, MapPin, DollarSign, Clock, ChevronDown, SlidersHorizontal, X } from "lucide-react";
import { cn } from "@/utils/cn";
import { geoApi } from "@/api/geo";
import type { GeocodeResult } from "@/types";

export interface VacancyFilterValues {
  search: string;
  city: string;
  salary_from: string;
  salary_to: string;
  schedule_type: string;
}

interface VacancyFiltersProps {
  values: VacancyFilterValues;
  onChange: (values: VacancyFilterValues) => void;
}

const SCHEDULE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "Любой график" },
  { value: "full_time", label: "Полная занятость" },
  { value: "part_time", label: "Частичная" },
  { value: "contract", label: "Договор подряда" },
  { value: "internship", label: "Стажировка" },
  { value: "gig", label: "Разовая / подработка" },
];

export default function VacancyFilters({ values, onChange }: VacancyFiltersProps): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  const [localSearch, setLocalSearch] = useState(values.search);
  const [cityQuery, setCityQuery] = useState("");
  const [citySuggestions, setCitySuggestions] = useState<GeocodeResult[]>([]);
  const [cityLoading, setCityLoading] = useState(false);
  const [cityOpen, setCityOpen] = useState(false);
  const cityContainerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const cityDebounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Sync external search value changes (e.g. from URL restore)
  useEffect(() => {
    setLocalSearch(values.search);
  }, [values.search]);

  // Debounced search
  const handleSearchChange = useCallback(
    (value: string) => {
      setLocalSearch(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onChange({ ...values, search: value });
      }, 300);
    },
    [onChange, values],
  );

  // City autocomplete with debounce
  const handleCityQueryChange = useCallback(
    (value: string) => {
      setCityQuery(value);
      if (cityDebounceRef.current) clearTimeout(cityDebounceRef.current);
      if (!value.trim()) {
        setCitySuggestions([]);
        setCityOpen(false);
        return;
      }
      cityDebounceRef.current = setTimeout(async () => {
        setCityLoading(true);
        try {
          const results = await geoApi.geocode(value);
          setCitySuggestions(results);
          setCityOpen(results.length > 0);
        } catch {
          setCitySuggestions([]);
        } finally {
          setCityLoading(false);
        }
      }, 300);
    },
    [],
  );

  // Select city from suggestions
  const handleCitySelect = useCallback(
    (cityName: string) => {
      setCityQuery("");
      setCityOpen(false);
      setCitySuggestions([]);
      onChange({ ...values, city: cityName });
    },
    [onChange, values],
  );

  // Remove selected city
  const handleCityClear = useCallback(() => {
    onChange({ ...values, city: "" });
  }, [onChange, values]);

  // Close city dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (cityContainerRef.current && !cityContainerRef.current.contains(e.target as Node)) {
        setCityOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Update a single field immediately
  const updateField = useCallback(
    (field: keyof VacancyFilterValues, value: string) => {
      onChange({ ...values, [field]: value });
    },
    [onChange, values],
  );

  const hasActiveFilters =
    values.search || values.city || values.salary_from || values.salary_to || values.schedule_type;

  const clearAll = useCallback(() => {
    onChange({ search: "", city: "", salary_from: "", salary_to: "", schedule_type: "" });
    setLocalSearch("");
    setCityQuery("");
    setCitySuggestions([]);
    setCityOpen(false);
  }, [onChange]);

  return (
    <div className="space-y-3" data-testid="vacancy-filters">
      {/* Mobile toggle */}
      <button
        type="button"
        className="btn-ghost flex w-full items-center justify-between lg:hidden"
        onClick={() => setExpanded((e) => !e)}
        data-testid="filters-toggle"
      >
        <span className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4" />
          Фильтры
          {hasActiveFilters && (
            <span className="chip bg-brand-100 text-brand-700 dark:bg-brand-900 dark:text-brand-300">
              Активны
            </span>
          )}
        </span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", expanded && "rotate-180")} />
      </button>

      <div className={cn("space-y-3", !expanded && "hidden lg:block")}>
        {/* Search input */}
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <input
            type="text"
            placeholder="Поиск по названию..."
            value={localSearch}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="input pl-10 pr-8"
            data-testid="filter-search"
            aria-label="Поиск вакансий"
          />
          {localSearch && (
            <button
              type="button"
              onClick={() => handleSearchChange("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400 hover:text-ink-600"
              aria-label="Очистить поиск"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* City input with autocomplete */}
        <div className="relative" ref={cityContainerRef}>
          <MapPin className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-ink-400" />
          {values.city ? (
            <div className="input flex items-center gap-2 pl-10 pr-2" data-testid="filter-city-selected">
              <span className="flex-1 text-sm">{values.city}</span>
              <button
                type="button"
                onClick={handleCityClear}
                className="rounded-full p-0.5 text-ink-400 hover:text-ink-600 hover:bg-ink-100"
                aria-label="Убрать город"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ) : (
            <>
              <input
                type="text"
                placeholder="Город..."
                value={cityQuery}
                onChange={(e) => handleCityQueryChange(e.target.value)}
                className="input pl-10"
                data-testid="filter-city"
                aria-label="Выбор города"
                autoComplete="off"
              />
              {cityLoading && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-400">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent inline-block" />
                </span>
              )}
            </>
          )}

          {/* City suggestions dropdown */}
          {cityOpen && !values.city && citySuggestions.length > 0 && (
            <ul
              className="absolute z-20 mt-1 w-full rounded-xl border border-ink-200 bg-white shadow-lg dark:border-ink-700 dark:bg-ink-900 max-h-48 overflow-auto"
              data-testid="filter-city-suggestions"
            >
              {citySuggestions.map((s, i) => (
                <li key={s.osm_id ?? i}>
                  <button
                    type="button"
                    className="w-full px-4 py-2 text-left text-sm hover:bg-ink-50 dark:hover:bg-ink-800 first:rounded-t-xl last:rounded-b-xl"
                    onClick={() => handleCitySelect(s.display_name ?? "")}
                  >
                    {s.display_name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Salary range */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <DollarSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <input
              type="number"
              placeholder="Зарплата от"
              value={values.salary_from}
              onChange={(e) => updateField("salary_from", e.target.value)}
              className="input pl-10"
              min="0"
              data-testid="filter-salary-from"
              aria-label="Зарплата от"
            />
          </div>
          <div className="relative flex-1">
            <DollarSign className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <input
              type="number"
              placeholder="до"
              value={values.salary_to}
              onChange={(e) => updateField("salary_to", e.target.value)}
              className="input pl-10"
              min="0"
              data-testid="filter-salary-to"
              aria-label="Зарплата до"
            />
          </div>
        </div>

        {/* Schedule type */}
        <div className="relative">
          <Clock className="pointer-events-none absolute left-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <select
            value={values.schedule_type}
            onChange={(e) => updateField("schedule_type", e.target.value)}
            className="input pl-10 pr-8 appearance-none cursor-pointer"
            data-testid="filter-schedule"
            aria-label="График работы"
          >
            {SCHEDULE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
        </div>

        {/* Clear all button */}
        {hasActiveFilters && (
          <button
            type="button"
            onClick={clearAll}
            className="btn-ghost w-full text-xs"
            data-testid="filter-clear-all"
          >
            <X className="h-3.5 w-3.5" />
            Сбросить все фильтры
          </button>
        )}
      </div>
    </div>
  );
}
