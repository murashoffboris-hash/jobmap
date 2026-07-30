import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HomePage from "./HomePage";
import * as vacanciesModule from "@/api/vacancies";
import type { Vacancy } from "@/types";

// Mock MapContainer
vi.mock("@/components/MapContainer", () => ({
  default: vi.fn((props: { points?: Array<{ salary?: string; title?: string }>; onMarkerClick?: () => void }) => (
    <div data-testid="map-container">
      {props.points?.map((p, i) => (
        <div key={i} data-testid="map-point" data-salary={p.salary ?? ""}>
          {p.salary}
        </div>
      ))}
    </div>
  )),
}));

// Mock VacancyFilters — test it separately
vi.mock("@/components/VacancyFilters", () => ({
  default: vi.fn(({ values, onChange }: { values: Record<string, string>; onChange: (v: Record<string, string>) => void }) => (
    <div data-testid="vacancy-filters">
      <input
        data-testid="filter-search"
        value={values.search ?? ""}
        onChange={(e) => onChange({ ...values, search: e.target.value })}
        placeholder="Поиск по названию..."
      />
      <input
        data-testid="filter-city"
        value={values.city ?? ""}
        onChange={(e) => onChange({ ...values, city: e.target.value })}
        placeholder="Город..."
      />
      <button data-testid="filter-clear-all" onClick={() => onChange({ search: "", city: "", salary_from: "", salary_to: "", schedule_type: "" })}>
        Сбросить
      </button>
    </div>
  )),
}));

// Mock useInfiniteScroll — return a stable sentinel callback
vi.mock("@/hooks/useInfiniteScroll", () => ({
  useInfiniteScroll: vi.fn(() => ({
    sentinelRef: vi.fn(),
    reset: vi.fn(),
  })),
}));

function buildVacancy(overrides: Partial<Vacancy> = {}): Vacancy {
  return {
    id: 42,
    title: "Frontend-разработчик",
    description: "React / TypeScript",
    salary_from: 2000,
    salary_to: 3500,
    currency: "USD",
    employment_type: "full_time",
    employer_id: 1,
    employer_name: "ООО Технологии",
    city: "Минск",
    latitude: 53.9,
    longitude: 27.56,
    is_active: true,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

function makeListResponse(items: Vacancy[], total?: number) {
  return { items, total: total ?? items.length, page: 1, page_size: 20 };
}

describe("HomePage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("передаёт salary в MapPoint из данных вакансии", async () => {
    vi.spyOn(vacanciesModule.vacanciesApi, "list").mockResolvedValue(
      makeListResponse([
        buildVacancy({ id: 1, title: "Frontend", salary_from: 500, salary_to: 2000, currency: "BYN", latitude: 53.9, longitude: 27.56 }),
        buildVacancy({ id: 2, title: "Backend", salary_from: 1000, salary_to: 3000, currency: "BYN", latitude: 53.91, longitude: 27.57 }),
      ]),
    );

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    const points = await screen.findAllByTestId("map-point");
    expect(points).toHaveLength(2);
    expect(points[0]).toHaveAttribute("data-salary", "500–2\u00a0000 BYN");
    expect(points[1]).toHaveAttribute("data-salary", "1\u00a0000–3\u00a0000 BYN");
  });

  it("передаёт пустой salary если from и to null", async () => {
    vi.spyOn(vacanciesModule.vacanciesApi, "list").mockResolvedValue(
      makeListResponse([
        buildVacancy({ id: 1, title: "No salary", salary_from: null, salary_to: null, currency: "BYN", latitude: 53.9, longitude: 27.56 }),
      ]),
    );

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    const points = await screen.findAllByTestId("map-point");
    expect(points).toHaveLength(1);
    expect(points[0]).toHaveAttribute("data-salary", "з/п не указана");
  });

  it("показывает сообщение когда вакансий нет", async () => {
    vi.spyOn(vacanciesModule.vacanciesApi, "list").mockResolvedValue(makeListResponse([]));

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Ничего не найдено/i)).toBeInTheDocument();
    });
  });

  it("показывает ошибку при неудачной загрузке", async () => {
    vi.spyOn(vacanciesModule.vacanciesApi, "list").mockRejectedValue(new Error("Сетевая ошибка"));

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("Сетевая ошибка")).toBeInTheDocument();
    });
  });

  it("отображает фильтры", async () => {
    vi.spyOn(vacanciesModule.vacanciesApi, "list").mockResolvedValue(makeListResponse([buildVacancy()]));

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("vacancy-filters")).toBeInTheDocument();
    });
  });

  it("передаёт параметры фильтрации в API при поиске", async () => {
    const mockList = vi.spyOn(vacanciesModule.vacanciesApi, "list").mockResolvedValue(makeListResponse([]));

    render(
      <MemoryRouter initialEntries={["/?search=бетон&city=Минск"]}>
        <HomePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(mockList).toHaveBeenCalledWith(
        expect.objectContaining({ search: "бетон", city: "Минск" }),
      );
    });
  });

  it("передаёт пустой total когда вакансий нет", async () => {
    vi.spyOn(vacanciesModule.vacanciesApi, "list").mockResolvedValue(makeListResponse([]));

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Ничего не найдено/i)).toBeInTheDocument();
    });
  });
});
