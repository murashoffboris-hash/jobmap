import { describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";
import { authApi } from "./auth";
import type { UpdateProfileRequest, User } from "@/types";

vi.mock("./client", () => ({
  apiClient: {
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
  role: "worker",
  is_active: true,
  created_at: "2026-07-23T10:00:00Z",
};

describe("authApi.updateProfile", () => {
  it("отправляет PATCH /auth/me и возвращает профиль", async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: response });

    await expect(authApi.updateProfile(request)).resolves.toEqual(response);
    expect(apiClient.patch).toHaveBeenCalledWith("/auth/me", request);
  });
});
