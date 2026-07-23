import { apiClient } from "./client";
import type { AuthTokens, LoginRequest, RegisterRequest, User } from "@/types";

export const authApi = {
  async login(data: LoginRequest): Promise<AuthTokens> {
    const res = await apiClient.post<AuthTokens>("/auth/login", data);
    return res.data;
  },

  async register(data: RegisterRequest): Promise<User> {
    const res = await apiClient.post<User>("/auth/register", data);
    return res.data;
  },

  async me(): Promise<User> {
    const res = await apiClient.get<User>("/auth/me");
    return res.data;
  },

  async logout(): Promise<void> {
    await apiClient.post("/auth/logout").catch(() => {});
  },
};
