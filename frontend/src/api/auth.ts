import { apiClient } from "./client";
import type {
  AuthTokens,
  LoginRequest,
  RegisterRequest,
  RegistrationRole,
  RegistrationUiRole,
  UpdateProfileRequest,
  UpdateRoleRequest,
  User,
} from "@/types";

export function toRegistrationRole(role: RegistrationUiRole): RegistrationRole {
  return role === "worker" ? "user" : role;
}

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

  async updateProfile(data: UpdateProfileRequest): Promise<User> {
    const res = await apiClient.patch<User>("/auth/me", data);
    return res.data;
  },

  async updateRole(role: RegistrationRole): Promise<User> {
    const data: UpdateRoleRequest = { role };
    const res = await apiClient.patch<User>("/users/me/role", data);
    return res.data;
  },

  async logout(): Promise<void> {
    await apiClient.post("/auth/logout").catch(() => {});
  },
};
