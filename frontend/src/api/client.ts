import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";

export const apiClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 15_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

const TOKEN_KEY = "jobmap.auth.access";
const REFRESH_TOKEN_KEY = "jobmap.auth.refresh";

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // localStorage недоступен (приватный режим и т.п.) — молча проглатываем.
  }
}

export function getRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setRefreshToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
    else localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // localStorage недоступен — молча проглатываем.
  }
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken();
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Флаг для предотвращения рекурсивного рефреша (когда сам /auth/refresh вернул 401)
let isRefreshing = false;
// Очередь запросов, ожидающих завершения рефреша
let refreshQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function clearTokens(): void {
  setAccessToken(null);
  setRefreshToken(null);
}

async function tryRefreshToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("Нет refresh_token");
  }
  const res = await axios.post<{ access_token: string; refresh_token: string }>(
    `${baseURL}/auth/refresh`,
    { refresh_token: refreshToken },
    {
      headers: { "Content-Type": "application/json" },
      // Не используем apiClient, чтобы избежать рекурсии через interceptors
    },
  );
  setAccessToken(res.data.access_token);
  setRefreshToken(res.data.refresh_token);
  return res.data.access_token;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Не рефрешим, если: не 401, уже ретраили, или запрос сам был на /auth/refresh
    if (
      error.response?.status !== 401 ||
      originalRequest?._retry ||
      originalRequest?.url === "/auth/refresh"
    ) {
      return Promise.reject(error);
    }

    // Если рефреш уже идёт — встаём в очередь
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        refreshQueue.push({ resolve, reject });
      }).then((newToken) => {
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }
        return apiClient(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const newToken = await tryRefreshToken();
      // Оповещаем очередь
      refreshQueue.forEach((p) => p.resolve(newToken));
      refreshQueue = [];
      // Повторяем исходный запрос
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
      }
      return apiClient(originalRequest);
    } catch (refreshError) {
      // Не удалось обновить — чистим оба токена, оповещаем очередь об ошибке
      clearTokens();
      refreshQueue.forEach((p) => p.reject(refreshError));
      refreshQueue = [];
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export interface ApiErrorBody {
  detail?: string;
  code?: string;
  fields?: Record<string, string>;
}

export function extractApiError(err: unknown): string {
  if (axios.isAxiosError<ApiErrorBody>(err)) {
    const body = err.response?.data;
    if (body?.detail) return body.detail;
    if (body?.fields) {
      return Object.entries(body.fields)
        .map(([k, v]) => `${k}: ${v}`)
        .join("; ");
    }
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Неизвестная ошибка";
}
