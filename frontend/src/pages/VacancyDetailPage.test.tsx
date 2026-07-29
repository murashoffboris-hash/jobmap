import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import VacancyDetailPage from "./VacancyDetailPage";
import { vacanciesApi } from "@/api/vacancies";
import { applicationsApi } from "@/api/applications";
import type { Vacancy, Application, ApplicationListResponse } from "@/types";

vi.mock("@/api/vacancies", () => ({
  vacanciesApi: {
    get: vi.fn(),
  },
}));

vi.mock("@/api/applications", () => ({
  applicationsApi: {
    create: vi.fn(),
    withdraw: vi.fn(),
    listByVacancy: vi.fn(),
    updateStatus: vi.fn(),
  },
}));

// Dynamic auth mock — controlled per test via mockAuthUser
const mockAuthUser = vi.fn();
vi.mock("@/store/auth", () => ({
  useAuthStore: (selector?: (s: unknown) => unknown) => {
    const state = mockAuthUser();
    return selector ? selector(state) : state;
  },
}));

const mockVacancy: Vacancy = {
  id: 10,
  title: "Frontend-разработчик",
  description: "Опыт от 2 лет",
  salary_from: 100000,
  salary_to: 200000,
  currency: "RUB",
  employment_type: "full_time",
  employer_id: 99,
  employer_name: "ООО ТехноПлюс",
  city: "Москва",
  latitude: 55.75,
  longitude: 37.62,
  is_active: true,
  created_at: "2026-07-01T10:00:00Z",
  updated_at: "2026-07-01T10:00:00Z",
};

const mockApplication: Application = {
  id: 1,
  user_id: 42,
  vacancy_id: 10,
  cover_letter: "Хочу у вас работать",
  status: "pending",
  vacancy_title: "Frontend-разработчик",
  employer_name: "ООО ТехноПлюс",
  applicant_name: "Иван Иванов",
  created_at: "2026-07-27T10:00:00Z",
  updated_at: "2026-07-27T10:00:00Z",
};

const mockAppsList: ApplicationListResponse = {
  items: [mockApplication],
  total: 3,
  page: 1,
  page_size: 50,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/vacancies/10"]}>
      <Routes>
        <Route path="/vacancies/:id" element={<VacancyDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("VacancyDetailPage — отклики (соискатель)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthUser.mockReturnValue({
      user: { id: 42, email: "ivan@test.com", full_name: "Иван", role: "user" },
    });
    vi.mocked(vacanciesApi.get).mockResolvedValue(mockVacancy);
    vi.mocked(applicationsApi.listByVacancy).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  });

  it("показывает кнопку «Откликнуться» для авторизованного не-владельца", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Откликнуться")).toBeInTheDocument();
    });
  });

  it("после успешного отклика показывает «Вы откликнулись» и кнопку «Отозвать отклик»", async () => {
    vi.mocked(applicationsApi.create).mockResolvedValue(mockApplication);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Откликнуться")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Откликнуться"));

    await waitFor(() => {
      expect(screen.getByText("Отклик на вакансию")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Отправить"));

    await waitFor(() => {
      expect(screen.getByText(/Вы откликнулись на эту вакансию/i)).toBeInTheDocument();
    });
    expect(screen.getByText("Отозвать отклик")).toBeInTheDocument();
  });

  it("кнопка «Отозвать отклик» вызывает withdraw API", async () => {
    vi.mocked(applicationsApi.create).mockResolvedValue(mockApplication);
    const withdrawnApp = { ...mockApplication, status: "withdrawn" as const };
    vi.mocked(applicationsApi.withdraw).mockResolvedValue(withdrawnApp);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Откликнуться")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Откликнуться"));
    await waitFor(() => {
      expect(screen.getByText("Отправить")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByText("Отправить"));

    await waitFor(() => {
      expect(screen.getByText("Отозвать отклик")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Отозвать отклик"));

    await waitFor(() => {
      expect(applicationsApi.withdraw).toHaveBeenCalledWith(1);
    });
  });

  it("при 409 показывает «Вы откликнулись» без ошибки и без кнопки отзыва", async () => {
    const axiosError = { isAxiosError: true, response: { status: 409, data: { detail: "Duplicate" } } };
    vi.mocked(applicationsApi.create).mockRejectedValue(axiosError);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Откликнуться")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Откликнуться"));
    await waitFor(() => {
      expect(screen.getByText("Отправить")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByText("Отправить"));

    await waitFor(() => {
      expect(screen.getByText(/Вы откликнулись на эту вакансию/i)).toBeInTheDocument();
    });
    // No error should be shown
    expect(screen.queryByText(/Duplicate/i)).not.toBeInTheDocument();
    // No withdraw button (no id)
    expect(screen.queryByText("Отозвать отклик")).not.toBeInTheDocument();
  });
});

describe("VacancyDetailPage — отклики (работодатель)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthUser.mockReturnValue({
      user: { id: 99, email: "owner@test.com", full_name: "Работодатель", role: "employer" },
    });
    vi.mocked(vacanciesApi.get).mockResolvedValue(mockVacancy);
  });

  it("показывает секцию «Отклики на вакансию» со счётчиком", async () => {
    vi.mocked(applicationsApi.listByVacancy).mockResolvedValue(mockAppsList);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Отклики на вакансию")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  it("кнопки «Принять» и «Отклонить» видны для pending-откликов", async () => {
    vi.mocked(applicationsApi.listByVacancy).mockResolvedValue(mockAppsList);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Принять")).toBeInTheDocument();
    });
    expect(screen.getByText("Отклонить")).toBeInTheDocument();
  });

  it("нажатие «Принять» вызывает updateStatus с accepted", async () => {
    vi.mocked(applicationsApi.listByVacancy).mockResolvedValue(mockAppsList);
    const acceptedApp = { ...mockApplication, status: "accepted" as const };
    vi.mocked(applicationsApi.updateStatus).mockResolvedValue(acceptedApp);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Принять")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Принять"));

    await waitFor(() => {
      expect(applicationsApi.updateStatus).toHaveBeenCalledWith(1, { status: "accepted" });
    });
  });

  it("нажатие «Отклонить» вызывает updateStatus с rejected", async () => {
    vi.mocked(applicationsApi.listByVacancy).mockResolvedValue(mockAppsList);
    const rejectedApp = { ...mockApplication, status: "rejected" as const };
    vi.mocked(applicationsApi.updateStatus).mockResolvedValue(rejectedApp);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Отклонить")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Отклонить"));

    await waitFor(() => {
      expect(applicationsApi.updateStatus).toHaveBeenCalledWith(1, { status: "rejected" });
    });
  });
});
