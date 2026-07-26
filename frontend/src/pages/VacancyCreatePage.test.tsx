import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { EmployerRoleRequiredError, vacanciesApi } from "@/api/vacancies";
import { categoriesApi } from "@/api/categories";
import VacancyCreatePage from "./VacancyCreatePage";

// Mock maplibre-gl — jsdom doesn't support WebGL
vi.mock("maplibre-gl", () => {
  const mockMap = {
    on: vi.fn(),
    remove: vi.fn(),
    addControl: vi.fn(),
    flyTo: vi.fn(),
  };
  return {
    default: {
      Map: vi.fn(() => mockMap),
      Marker: vi.fn(() => ({
        setLngLat: vi.fn().mockReturnThis(),
        addTo: vi.fn().mockReturnThis(),
        remove: vi.fn(),
      })),
      NavigationControl: vi.fn(),
      ScaleControl: vi.fn(),
      LngLatBounds: vi.fn(() => ({
        extend: vi.fn().mockReturnThis(),
        isEmpty: vi.fn(() => true),
      })),
      Popup: vi.fn(() => ({
        setHTML: vi.fn().mockReturnThis(),
      })),
    },
  };
});

// Mock dependencies
vi.mock("@/api/vacancies", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/vacancies")>();
  return { ...actual, vacanciesApi: { ...actual.vacanciesApi, create: vi.fn() } };
});
vi.mock("@/api/categories", () => ({
  categoriesApi: { list: vi.fn().mockResolvedValue([]) },
}));
vi.mock("@/api/geo", () => ({
  geoApi: {
    geocode: vi.fn().mockResolvedValue([
      { display_name: "Минск, Беларусь", lat: 53.9, lon: 27.56, osm_id: "1", type: "city" },
    ]),
    reverse: vi.fn().mockResolvedValue({
      display_name: "Улица Ленина, Минск", lat: 53.9, lon: 27.56, osm_id: "2", type: "street",
    }),
  },
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

async function renderPage() {
  let result: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <VacancyCreatePage />
      </MemoryRouter>,
    );
  });
  return result!;
}

describe("VacancyCreatePage", () => {
  it("рендерит форму со всеми полями", async () => {
    await renderPage();
    expect(screen.getByLabelText("Название вакансии *")).toBeInTheDocument();
    expect(screen.getByLabelText("Адрес места работы")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Опубликовать вакансию" })).toBeInTheDocument();
  });

  it("кнопка отправки заблокирована при коротком названии", async () => {
    await renderPage();
    const btn = screen.getByRole("button", { name: "Опубликовать вакансию" });
    expect(btn).toBeDisabled();
  });

  it("отправляет форму с минимальными данными", async () => {
    vi.mocked(vacanciesApi.create).mockResolvedValue({
      id: 1, title: "Test", description: null, status: "active",
      address_normalized: null, location_lat: null, location_lon: null,
      geocode_status: "not_requested", salary_from: null, salary_to: null,
      salary_currency: "BYN", schedule_type: null, contact_phone: null,
      exact_location_public: false, created_at: "2025-01-01T00:00:00Z",
    } as never);

    await renderPage();
    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "Frontend-разработчик" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Опубликовать вакансию" }));

    await waitFor(() => {
      expect(vacanciesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Frontend-разработчик",
          salary_currency: "BYN",
        }),
      );
    });
  });

  it("отправляет все поля формы", async () => {
    vi.mocked(vacanciesApi.create).mockResolvedValue({
      id: 2, title: "Developer", description: "Desc", status: "active",
      address_normalized: "Минск", location_lat: 53.9, location_lon: 27.56,
      geocode_status: "success", salary_from: 1000, salary_to: 3000,
      salary_currency: "USD", schedule_type: "full_time", contact_phone: "+375291234567",
      exact_location_public: true, created_at: "2025-01-01T00:00:00Z",
    } as never);

    vi.mocked(categoriesApi.list).mockResolvedValue([
      { id: 1, name: "IT", slug: "it", parent_id: null },
    ]);

    await renderPage();

    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "Developer" },
    });
    // Fill in salary
    const salaryInputs = screen.getAllByPlaceholderText("0");
    fireEvent.change(salaryInputs[0], { target: { value: "1000" } });
    fireEvent.change(salaryInputs[1], { target: { value: "3000" } });

    fireEvent.click(screen.getByRole("button", { name: "Опубликовать вакансию" }));

    await waitFor(() => {
      expect(vacanciesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Developer",
          salary_from: 1000,
          salary_to: 3000,
        }),
      );
    });
  });

  it("при 403 показывает объяснение и ссылку на смену роли", async () => {
    vi.mocked(vacanciesApi.create).mockRejectedValue(new EmployerRoleRequiredError());
    await renderPage();

    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "Frontend-разработчик" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Опубликовать вакансию" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Создавать вакансии может только работодатель",
    );
    expect(screen.getByRole("link", { name: "Сменить роль в профиле" })).toHaveAttribute(
      "href",
      "/profile",
    );
  });

  it("валидирует salary_from > salary_to", async () => {
    vi.mocked(vacanciesApi.create).mockResolvedValue({ id: 1 } as never);
    await renderPage();

    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "Тестовая вакансия" },
    });
    const salaryInputs = screen.getAllByPlaceholderText("0");
    fireEvent.change(salaryInputs[0], { target: { value: "5000" } });
    fireEvent.change(salaryInputs[1], { target: { value: "1000" } });

    fireEvent.click(screen.getByRole("button", { name: "Опубликовать вакансию" }));

    await waitFor(() => {
      expect(screen.getByText("Максимальная зарплата не может быть меньше минимальной")).toBeInTheDocument();
    });
    // API не должен вызываться при ошибке валидации
    expect(vacanciesApi.create).not.toHaveBeenCalled();
  });

  it("кнопка отправки заблокирована при коротком названии (меньше 3 символов)", async () => {
    vi.mocked(vacanciesApi.create).mockResolvedValue({ id: 1 } as never);
    await renderPage();

    // Вводим 2 символа — кнопка должна быть заблокирована
    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "AB" },
    });

    const btn = screen.getByRole("button", { name: "Опубликовать вакансию" });
    expect(btn).toBeDisabled();
    fireEvent.click(btn);
    // API не должен вызываться, поскольку кнопка disabled
    expect(vacanciesApi.create).not.toHaveBeenCalled();
  });

  it("обрабатывает API ошибку (не 403)", async () => {
    vi.mocked(vacanciesApi.create).mockRejectedValue(new Error("Серверная ошибка"));
    await renderPage();

    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "Frontend-разработчик" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Опубликовать вакансию" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Серверная ошибка");
  });
});
