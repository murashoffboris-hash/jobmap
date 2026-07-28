import { create } from "zustand";
import { authApi } from "@/api/auth";
import { getAccessToken, setAccessToken, setRefreshToken } from "@/api/client";
import type { LoginRequest, RegisterRequest, User } from "@/types";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "authenticated" | "error";
  error: string | null;
  bootstrap: () => Promise<void>;
  login: (req: LoginRequest) => Promise<void>;
  register: (req: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: "idle",
  error: null,

  async bootstrap() {
    if (!getAccessToken()) {
      set({ status: "idle", user: null });
      return;
    }
    set({ status: "loading", error: null });
    try {
      const user = await authApi.me();
      set({ user, status: "authenticated" });
    } catch {
      setAccessToken(null);
      setRefreshToken(null);
      set({ user: null, status: "idle" });
    }
  },

  async login(req) {
    set({ status: "loading", error: null });
    try {
      const tokens = await authApi.login(req);
      setAccessToken(tokens.access_token);
      setRefreshToken(tokens.refresh_token);
      const user = await authApi.me();
      set({ user, status: "authenticated" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ошибка входа";
      set({ status: "error", error: message, user: null });
      throw err;
    }
  },

  async register(req) {
    set({ status: "loading", error: null });
    try {
      await authApi.register(req);
      // Сразу логиним — упрощённый UX для MVP.
      await useAuthStore.getState().login({ email: req.email, password: req.password });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Ошибка регистрации";
      set({ status: "error", error: message });
      throw err;
    }
  },

  async logout() {
    try {
      await authApi.logout();
    } catch {
      // даже если запрос упал — чистим локальное состояние
    } finally {
      setAccessToken(null);
      setRefreshToken(null);
      set({ user: null, status: "idle", error: null });
    }
  },

  updateUser(user) {
    set({ user, status: "authenticated", error: null });
  },

  clearError() {
    set({ error: null });
  },
}));
