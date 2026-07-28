import { describe, expect, it, vi, beforeEach } from "vitest";
import { useAuthStore } from "./auth";

// Мокаем API
vi.mock("@/api/auth", () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}));

// Мокаем client (токены)
const tokenStore = new Map<string, string>();
vi.mock("@/api/client", () => ({
  getAccessToken: vi.fn(() => tokenStore.get("access") ?? null),
  setAccessToken: vi.fn((token: string | null) => {
    if (token) tokenStore.set("access", token);
    else tokenStore.delete("access");
  }),
  getRefreshToken: vi.fn(() => tokenStore.get("refresh") ?? null),
  setRefreshToken: vi.fn((token: string | null) => {
    if (token) tokenStore.set("refresh", token);
    else tokenStore.delete("refresh");
  }),
  apiClient: {},
  extractApiError: vi.fn(),
}));

import { authApi } from "@/api/auth";
import { setAccessToken, setRefreshToken } from "@/api/client";

const mockUser = {
  id: 1,
  email: "test@example.com",
  full_name: "Тест Тестов",
  phone: null,
  bio: null,
  avatar_url: null,
  role: "user" as const,
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

describe("useAuthStore — refresh_token", () => {
  beforeEach(() => {
    tokenStore.clear();
    vi.clearAllMocks();
    useAuthStore.setState({ user: null, status: "idle", error: null });
  });

  it("login сохраняет оба токена (access + refresh)", async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce({
      access_token: "access-abc",
      refresh_token: "refresh-xyz",
      token_type: "bearer",
    });
    vi.mocked(authApi.me).mockResolvedValueOnce(mockUser);

    await useAuthStore.getState().login({ email: "test@example.com", password: "pass" });

    expect(setAccessToken).toHaveBeenCalledWith("access-abc");
    expect(setRefreshToken).toHaveBeenCalledWith("refresh-xyz");
    expect(tokenStore.get("access")).toBe("access-abc");
    expect(tokenStore.get("refresh")).toBe("refresh-xyz");
  });

  it("logout чистит оба токена", async () => {
    // Предварительно «залогинились»
    tokenStore.set("access", "old-access");
    tokenStore.set("refresh", "old-refresh");
    useAuthStore.setState({ user: mockUser, status: "authenticated" });

    vi.mocked(authApi.logout).mockResolvedValueOnce(undefined);

    await useAuthStore.getState().logout();

    expect(tokenStore.has("access")).toBe(false);
    expect(tokenStore.has("refresh")).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().status).toBe("idle");
  });

  it("logout чистит токены даже при ошибке API", async () => {
    tokenStore.set("access", "old-access");
    tokenStore.set("refresh", "old-refresh");
    useAuthStore.setState({ user: mockUser, status: "authenticated" });

    vi.mocked(authApi.logout).mockRejectedValueOnce(new Error("Network error"));

    await useAuthStore.getState().logout();

    expect(tokenStore.has("access")).toBe(false);
    expect(tokenStore.has("refresh")).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("bootstrap чистит оба токена при ошибке me()", async () => {
    tokenStore.set("access", "stale-access");
    tokenStore.set("refresh", "stale-refresh");

    vi.mocked(authApi.me).mockRejectedValueOnce(new Error("401"));

    await useAuthStore.getState().bootstrap();

    expect(tokenStore.has("access")).toBe(false);
    expect(tokenStore.has("refresh")).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().status).toBe("idle");
  });
});
