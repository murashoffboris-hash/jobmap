import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { EmployerRoleRequiredError, vacanciesApi } from "@/api/vacancies";
import VacancyCreatePage from "./VacancyCreatePage";

vi.mock("@/api/vacancies", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/vacancies")>();
  return { ...actual, vacanciesApi: { ...actual.vacanciesApi, create: vi.fn() } };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("VacancyCreatePage", () => {
  it("при 403 показывает объяснение и ссылку на смену роли", async () => {
    vi.mocked(vacanciesApi.create).mockRejectedValue(new EmployerRoleRequiredError());
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <VacancyCreatePage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Название вакансии"), {
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
    await waitFor(() => expect(vacanciesApi.create).toHaveBeenCalled());
  });
});
