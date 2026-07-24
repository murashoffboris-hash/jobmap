import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { authApi } from "@/api/auth";
import { useAuthStore } from "@/store/auth";
import type { User } from "@/types";
import ProfilePage from "./ProfilePage";

vi.mock("@/api/auth", () => ({
  authApi: {
    updateProfile: vi.fn(),
  },
}));

const user: User = {
  id: 7,
  email: "ivan@example.com",
  full_name: "Иван Петров",
  phone: "+375291234567",
  bio: "Frontend-разработчик",
  avatar_url: null,
  role: "worker",
  is_active: true,
  created_at: "2026-07-23T10:00:00Z",
};

function renderPage(): void {
  render(
    <MemoryRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <ProfilePage />
    </MemoryRouter>,
  );
}

describe("ProfilePage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user,
      status: "authenticated",
      error: null,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("показывает данные текущего пользователя", () => {
    renderPage();

    expect(screen.getByRole("heading", { name: "Иван Петров" })).toBeInTheDocument();
    expect(screen.getByText("ivan@example.com")).toBeInTheDocument();
    expect(screen.getByText("+375291234567")).toBeInTheDocument();
    expect(screen.getByText("Frontend-разработчик")).toBeInTheDocument();
  });

  it("валидирует обязательное имя до отправки формы", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    fireEvent.change(screen.getByLabelText("Имя и фамилия"), { target: { value: "  " } });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    expect(await screen.findByText("Укажите имя и фамилию")).toBeInTheDocument();
    expect(authApi.updateProfile).not.toHaveBeenCalled();
  });

  it("сохраняет профиль и сразу обновляет данные в интерфейсе", async () => {
    const updatedUser: User = {
      ...user,
      full_name: "Иван Иванов",
      phone: "+375291111111",
      bio: "Ищу проектную работу",
    };
    vi.mocked(authApi.updateProfile).mockResolvedValue(updatedUser);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    fireEvent.change(screen.getByLabelText("Имя и фамилия"), {
      target: { value: " Иван Иванов " },
    });
    fireEvent.change(screen.getByLabelText("Телефон"), {
      target: { value: "+375291111111" },
    });
    fireEvent.change(screen.getByLabelText("О себе"), {
      target: { value: "Ищу проектную работу" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Сохранить" }));

    await waitFor(() => {
      expect(authApi.updateProfile).toHaveBeenCalledWith({
        full_name: "Иван Иванов",
        phone: "+375291111111",
        bio: "Ищу проектную работу",
      });
    });
    expect(await screen.findByRole("heading", { name: "Иван Иванов" })).toBeInTheDocument();
    expect(screen.getByText("Профиль сохранён")).toBeInTheDocument();
    expect(useAuthStore.getState().user).toEqual(updatedUser);
  });

  it("отменяет несохранённые изменения", () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Редактировать" }));
    fireEvent.change(screen.getByLabelText("Имя и фамилия"), {
      target: { value: "Другое имя" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Отмена" }));

    expect(screen.getByRole("heading", { name: "Иван Петров" })).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Другое имя")).not.toBeInTheDocument();
  });
});
