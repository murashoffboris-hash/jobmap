import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { extractApiError } from "@/api/client";
import type { UserRole } from "@/types";

export default function RegisterPage(): JSX.Element {
  const navigate = useNavigate();
  const register = useAuthStore((s) => s.register);
  const status = useAuthStore((s) => s.status);
  const error = useAuthStore((s) => s.error);
  const clearError = useAuthStore((s) => s.clearError);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("worker");
  const [localError, setLocalError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    setLocalError(null);
    clearError();
    if (password.length < 6) {
      setLocalError("Пароль должен быть не короче 6 символов");
      return;
    }
    try {
      await register({ email: email.trim(), password, full_name: fullName.trim(), role });
      navigate("/", { replace: true });
    } catch (err) {
      setLocalError(extractApiError(err));
    }
  }

  return (
    <div className="page">
      <h1 className="page__title">Регистрация</h1>
      <form className="form" onSubmit={onSubmit} noValidate>
        <label className="form__label">
          Имя
          <input
            className="input"
            type="text"
            required
            minLength={2}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </label>
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
            autoComplete="new-password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="form__label">
          Я ищу…
          <select
            className="input"
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
          >
            <option value="worker">Работу</option>
            <option value="employer">Сотрудников</option>
          </select>
        </label>
        {(localError || error) && <p className="form__error">{localError ?? error}</p>}
        <button type="submit" className="btn btn--primary" disabled={status === "loading"}>
          {status === "loading" ? "Создаём…" : "Зарегистрироваться"}
        </button>
        <p className="muted">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  );
}
