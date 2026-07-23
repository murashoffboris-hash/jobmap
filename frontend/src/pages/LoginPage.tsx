import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { extractApiError } from "@/api/client";

export default function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);
  const status = useAuthStore((s) => s.status);
  const error = useAuthStore((s) => s.error);
  const clearError = useAuthStore((s) => s.clearError);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setLocalError(null);
    clearError();
    try {
      await login({ email: email.trim(), password });
      navigate("/", { replace: true });
    } catch (err) {
      setLocalError(extractApiError(err));
    }
  }

  return (
    <div className="page">
      <h1 className="page__title">Вход</h1>
      <form className="form" onSubmit={onSubmit} noValidate>
        <label className="form__label">
          Email
          <input
            className="input"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="form__label">
          Пароль
          <input
            className="input"
            type="password"
            autoComplete="current-password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {(localError || error) && <p className="form__error">{localError ?? error}</p>}
        <button type="submit" className="btn btn--primary" disabled={status === "loading"}>
          {status === "loading" ? "Входим…" : "Войти"}
        </button>
        <p className="muted">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </form>
    </div>
  );
}
