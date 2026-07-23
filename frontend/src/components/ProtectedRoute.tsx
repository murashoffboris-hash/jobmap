import { type ReactElement, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { getAccessToken } from "@/api/client";

interface ProtectedRouteProps {
  children: ReactElement;
  /** Куда редиректить без токена. По умолчанию /login. */
  redirectTo?: string;
}

/**
 * Обёртка для защищённых маршрутов.
 *
 * Логика:
 *  1. Нет access-токена в localStorage → редирект на /login (с from-state).
 *  2. Есть токен, но статус "idle" — пытаемся bootstrap-ом подтянуть профиль
 *     (GET /auth/me). На время показываем спиннер, не редиректим сразу —
 *     токен мог быть валидным, просто ещё не подтверждён.
 *  3. Если bootstrap отдал ошибку (401 и т.п.) — токен протух/невалиден,
 *     редиректим на /login.
 *  4. Если user есть — рендерим children.
 */
export default function ProtectedRoute({
  children,
  redirectTo = "/login",
}: ProtectedRouteProps): ReactElement {
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const status = useAuthStore((s) => s.status);
  const error = useAuthStore((s) => s.error);
  const bootstrap = useAuthStore((s) => s.bootstrap);

  const [bootstrapped, setBootstrapped] = useState(
    () => !getAccessToken() || status !== "idle",
  );

  useEffect(() => {
    if (!getAccessToken()) return;
    if (status === "idle") {
      void bootstrap().finally(() => setBootstrapped(true));
    } else {
      setBootstrapped(true);
    }
  }, [bootstrap, status]);

  // Нет токена — сразу на логин, сохраняем откуда пришли.
  if (!getAccessToken()) {
    return <Navigate to={redirectTo} replace state={{ from: location.pathname + location.search }} />;
  }

  // Токен есть, но мы ещё не успели проверить его валидность.
  if (!bootstrapped || (status === "loading" && !user)) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-brand-500" aria-label="Проверка сессии" />
      </div>
    );
  }

  // После bootstrap без пользователя и с ошибкой — на логин.
  if (!user) {
    return <Navigate to={redirectTo} replace state={{ from: location.pathname + location.search }} />;
  }

  // Bootstrap дал ошибку (например, сеть) — пользователь остаётся,
  // но мы не блокируем страницу. Можно отобразить баннер.
  if (error && status === "error") {
    // Fallthrough: продолжаем показывать children; auth store сам разрулит UI.
  }

  return children;
}
