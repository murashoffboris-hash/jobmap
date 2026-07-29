import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HomePage from "./HomePage";
import * as vacanciesModule from "@/api/vacancies";
import type { Vacancy } from "@/types";

// Мокаем MapContainer — проверяем переданные пропсы
vi.mock("@/components/MapContainer", () => ({
  default: vi.fn((props: { points?: Array<{ salary?: string }>; onMarkerClick?: () => void }) => {
    return (
      <div data-testid="map-container">
        {props.points?.map((p, i) => (
          <div key={i} data-testid="map-point" data-salary={p.salary ?? ""}>
            {p.salary}
          </div>
        ))}
      </div>
    );
  }),
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

describe("HomePage", () => {
  it("передаёт salary в MapPoint из данных вакансии", async () => {
    const mockList = vi
      .spyOn(vacanciesModule.vacanciesApi, "list")
      .mockResolvedValue({
        items: [
          buildVacancy({
            id: 1,
            title: "Frontend",
            salary_from: 500,
            salary_to: 2000,
            currency: "BYN",
            latitude: 53.9,
            longitude: 27.56,
          }),
          buildVacancy({
            id: 2,
            title: "Backend",
            salary_from: 1000,
            salary_to: 3000,
            currency: "BYN",
            latitude: 53.91,
            longitude: 27.57,
          }),
        ],
        total: 2,
        page: 1,
        page_size: 20,
      });

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    const points = await screen.findAllByTestId("map-point");
    expect(points).toHaveLength(2);
    expect(points[0]).toHaveAttribute("data-salary", "500–2\u00a0000 BYN");
    expect(points[1]).toHaveAttribute("data-salary", "1\u00a0000–3\u00a0000 BYN");

    mockList.mockRestore();
  });

  it("передаёт пустой salary если from и to null", async () => {
    const mockList = vi
      .spyOn(vacanciesModule.vacanciesApi, "list")
      .mockResolvedValue({
        items: [
          buildVacancy({
            id: 1,
            title: "No salary",
            salary_from: null,
            salary_to: null,
            currency: "BYN",
            latitude: 53.9,
            longitude: 27.56,
          }),
        ],
        total: 1,
        page: 1,
        page_size: 20,
      });

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );

    const points = await screen.findAllByTestId("map-point");
    expect(points).toHaveLength(1);
    // "з/п не указана" с неразрывным пробелом (формат formatSalary)
    expect(points[0]).toHaveAttribute("data-salary", "з/п не указана");

    mockList.mockRestore();
  });
});
