import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
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

// jsdom не реализует window.confirm — мокаем глобально
beforeAll(() => {
  vi.stubGlobal("confirm", vi.fn(() => true));
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  // Возвращаем confirm по умолчанию (true)
  vi.mocked(window.confirm).mockReturnValue(true);
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
    expect(screen.getByText("Адрес места работы (обязательно для карты)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Опубликовать вакансию" })).toBeInTheDocument();
  });

  it("показывает hint под полем адреса", async () => {
    await renderPage();
    expect(screen.getByText(/Укажите адрес, чтобы вакансия отображалась на карте/)).toBeInTheDocument();
  });

  it("кнопка отправки заблокирована при коротком названии", async () => {
    await renderPage();
    const btn = screen.getByRole("button", { name: "Опубликовать вакансию" });
    expect(btn).toBeDisabled();
  });

  it("отправляет форму с минимальными данными (с confirm-диалогом)", async () => {
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
      expect(window.confirm).toHaveBeenCalledWith(
        "Без адреса вакансия не появится на карте. Продолжить?"
      );
    });

    await waitFor(() => {
      expect(vacanciesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Frontend-разработчик",
          salary_currency: "BYN",
        }),
      );
    });
  });

  it("не отправляет форму если пользователь отказался в confirm-диалоге", async () => {
    vi.mocked(vacanciesApi.create).mockResolvedValue({ id: 1 } as never);
    vi.mocked(window.confirm).mockReturnValue(false);

    await renderPage();
    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "Frontend-разработчик" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Опубликовать вакансию" }));

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
    });
    expect(vacanciesApi.create).not.toHaveBeenCalled();
  });

  it("отправляет все поля формы", async () => {
    vi.mocked(vacanciesApi.create).mockResolvedValue({
      id: 2, title: "Developer", description: "Desc", status: "active",
      address_normalized: "Минск", location_lat: 53.9, location_lon: 27.56,
      geocode_status: "success", salary_from: 1000, salary_to: 3000,
      salary_currency: "USD", schedule_type: "full_time", contact_phone: "+375****4567",
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

  it("обрабатывает API ошибку и показывает сообщение", async () => {
    vi.mocked(vacanciesApi.create).mockRejectedValue(new Error("Серверная ошибка"));
    await renderPage();

    fireEvent.change(screen.getByLabelText("Название вакансии *"), {
      target: { value: "Frontend-разработчик" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Опубликовать вакансию" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Серверная ошибка");
  });

  it("показывает ошибку загрузки категорий и кнопку retry", async () => {
    vi.mocked(categoriesApi.list).mockRejectedValue(new Error("Network Error"));

    await renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Network Error/)).toBeInTheDocument();
    });
    expect(screen.getByText("Повторить загрузку")).toBeInTheDocument();
  });

  it("повторяет загрузку категорий по кнопке retry", async () => {
    vi.mocked(categoriesApi.list)
      .mockRejectedValueOnce(new Error("Network Error"))
      .mockResolvedValueOnce([{ id: 1, name: "IT", slug: "it", parent_id: null }]);

    await renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Network Error/)).toBeInTheDocument();
    });

    // Нажимаем retry
    fireEvent.click(screen.getByText("Повторить загрузку"));

    await waitFor(() => {
      expect(screen.getByText("IT")).toBeInTheDocument();
    });
  });

  it("показывает loading при загрузке категорий", async () => {
    // Не резолвим промис — оставляем в состоянии loading
    vi.mocked(categoriesApi.list).mockReturnValue(new Promise(() => {}));

    await renderPage();

    expect(screen.getByText("Загрузка категорий...")).toBeInTheDocument();
  });
});
