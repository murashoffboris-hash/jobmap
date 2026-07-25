import { describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";
import { authApi, toRegistrationRole } from "./auth";
import type { UpdateProfileRequest, User } from "@/types";

vi.mock("./client", () => ({
  apiClient: {
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const request: UpdateProfileRequest = {
  full_name: "Иван Петров",
  phone: "+375291234567",
  bio: "Frontend-разработчик",
};

const response: User = {
  id: 7,
  email: "ivan@example.com",
  ...request,
  avatar_url: null,
  role: "user",
  is_active: true,
  created_at: "2026-07-23T10:00:00Z",
};

describe("маппинг роли при регистрации", () => {
  it("маппит UI-роль соискателя worker на backend-роль user", () => {
    expect(toRegistrationRole("worker")).toBe("user");
  });

  it("оставляет роль работодателя без изменений", () => {
    expect(toRegistrationRole("employer")).toBe("employer");
  });
});

describe("authApi", () => {
  it("отправляет PATCH /auth/me и возвращает профиль", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: response });

    await expect(authApi.updateProfile(request)).resolves.toEqual(response);
    expect(apiClient.patch).toHaveBeenCalledWith("/auth/me", request);
  });

  it("переключает роль через PATCH /users/me/role", async () => {
    const employer = { ...response, role: "employer" as const };
    vi.mocked(apiClient.patch).mockResolvedValue({ data: employer });

    await expect(authApi.updateRole("employer")).resolves.toEqual(employer);
    expect(apiClient.patch).toHaveBeenCalledWith("/users/me/role", { role: "employer" });
  });
});
