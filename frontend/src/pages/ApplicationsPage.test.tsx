import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import ApplicationsPage from "./ApplicationsPage";
import { applicationsApi } from "@/api/applications";
import type { Application, ApplicationListResponse } from "@/types";

vi.mock("@/api/applications", () => ({
  applicationsApi: {
    listMy: vi.fn(),
    withdraw: vi.fn(),
  },
}));

vi.mock("@/store/auth", () => ({
  useAuthStore: () => ({
    user: { id: 42, email: "test@test.com", full_name: "Иван", role: "user" },
  }),
}));

const mockApp: Application = {
  id: 1,
  user_id: 42,
  vacancy_id: 10,
  cover_letter: "Очень хочу у вас работать",
  status: "pending",
  vacancy_title: "Frontend-разработчик",
  employer_name: "ООО ТехноПлюс",
  applicant_name: "Иван Иванов",
  created_at: "2026-07-27T10:00:00Z",
  updated_at: "2026-07-27T10:00:00Z",
};

const mockList: ApplicationListResponse = {
  items: [mockApp],
  total: 1,
  page: 1,
  page_size: 10,
};

const emptyList: ApplicationListResponse = {
  items: [],
  total: 0,
  page: 1,
  page_size: 10,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/applications"]}>
      <ApplicationsPage />
    </MemoryRouter>,
  );
}

describe("ApplicationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("показывает загрузку при первом рендере", () => {
    vi.mocked(applicationsApi.listMy).mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByText("Загрузка…")).toBeInTheDocument();
  });

  it("показывает пустое состояние когда нет откликов", async () => {
    vi.mocked(applicationsApi.listMy).mockResolvedValue(emptyList);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/У вас пока нет откликов/i)).toBeInTheDocument();
    });
  });

  it("отображает список откликов со статус-бейджами", async () => {
    vi.mocked(applicationsApi.listMy).mockResolvedValue(mockList);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Frontend-разработчик")).toBeInTheDocument();
    });
    expect(screen.getByText("ООО ТехноПлюс")).toBeInTheDocument();
    expect(screen.getByText("На рассмотрении")).toBeInTheDocument();
  });

  it("показывает кнопку «Отозвать» для pending-откликов", async () => {
    vi.mocked(applicationsApi.listMy).mockResolvedValue(mockList);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Отозвать")).toBeInTheDocument();
    });
  });

  it("показывает подтверждение при нажатии «Отозвать» и выполняет отзыв", async () => {
    vi.mocked(applicationsApi.listMy).mockResolvedValue(mockList);
    const withdrawnApp = { ...mockApp, status: "withdrawn" as const };
    vi.mocked(applicationsApi.withdraw).mockResolvedValue(withdrawnApp);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Отозвать")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Отозвать"));
    expect(screen.getByText("Да, отозвать")).toBeInTheDocument();
    expect(screen.getByText("Нет")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Да, отозвать"));
    await waitFor(() => {
      expect(applicationsApi.withdraw).toHaveBeenCalledWith(1);
    });
  });

  it("отображает статус «Принято» с зелёным бейджем", async () => {
    const acceptedApp = { ...mockApp, status: "accepted" as const };
    vi.mocked(applicationsApi.listMy).mockResolvedValue({
      ...mockList,
      items: [acceptedApp],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Принято")).toBeInTheDocument();
    });
    // Не должен показывать кнопку отзыва для accepted
    expect(screen.queryByText("Отозвать")).not.toBeInTheDocument();
  });

  it("отображает статус «Отклонено» с красным бейджем", async () => {
    const rejectedApp = { ...mockApp, status: "rejected" as const };
    vi.mocked(applicationsApi.listMy).mockResolvedValue({
      ...mockList,
      items: [rejectedApp],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Отклонено")).toBeInTheDocument();
    });
  });

  it("отображает статус «Отозвано» с серым бейджем", async () => {
    const withdrawnApp = { ...mockApp, status: "withdrawn" as const };
    vi.mocked(applicationsApi.listMy).mockResolvedValue({
      ...mockList,
      items: [withdrawnApp],
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Отозвано")).toBeInTheDocument();
    });
  });
});
