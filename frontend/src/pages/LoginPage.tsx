import { useState, type FormEvent } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { Mail, Lock, LogIn, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { extractApiError } from "@/api/client";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/Button";
import Input from "@/components/Input";

interface LocationState {
  from?: string;
}

export default function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const fromPath = (location.state as LocationState | null)?.from ?? "/";

  const login = useAuthStore((s) => s.login);
  const status = useAuthStore((s) => s.status);
  const clearError = useAuthStore((s) => s.clearError);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  function validate(): boolean {
    let ok = true;
    setEmailError(null);
    setPasswordError(null);
    setFormError(null);

    const trimmed = email.trim();
    if (!trimmed) {
      setEmailError("Введите email");
      ok = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setEmailError("Похоже на некорректный email");
      ok = false;
    }

    if (!password) {
      setPasswordError("Введите пароль");
      ok = false;
    } else if (password.length < 6) {
      setPasswordError("Пароль должен быть не короче 6 символов");
      ok = false;
    }
    return ok;
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>): Promise<void> {
    e.preventDefault();
    if (!validate()) return;
    clearError();
    setFormError(null);
    try {
      await login({ email: email.trim(), password });
      navigate(fromPath, { replace: true });
    } catch (err) {
      const msg = extractApiError(err);
      // 401 → "неверный пароль", 404 → "пользователь не найден". Показываем как общую ошибку формы.
      setFormError(msg || "Не удалось войти. Проверьте email и пароль.");
    }
  }

  const loading = status === "loading";

  return (
    <AuthShell
      title="С возвращением 👋"
      subtitle="Войдите, чтобы откликаться на вакансии и видеть предложения рядом."
      footer={
        <span className="muted">
          Нет аккаунта?{" "}
          <Link to="/register" className="font-medium text-brand-700 hover:underline dark:text-brand-300">
            Зарегистрироваться
          </Link>
        </span>
      }
    >
      <motion.form
        onSubmit={onSubmit}
        noValidate
        className="space-y-4"
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.05 }}
      >
        <Input
          label="Email"
          type="email"
          name="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          leftIcon={<Mail size={16} />}
          error={emailError}
          disabled={loading}
          required
        />

        <Input
          label="Пароль"
          type="password"
          name="password"
          autoComplete="current-password"
          placeholder="Не менее 6 символов"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          leftIcon={<Lock size={16} />}
          error={passwordError}
          disabled={loading}
          required
        />

        {formError && (
          <motion.div
            role="alert"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
          >
            <AlertCircle size={16} className="mt-0.5 shrink-0" />
            <span>{formError}</span>
          </motion.div>
        )}

        <Button
          type="submit"
          variant="primary"
          size="lg"
          fullWidth
          loading={loading}
          leftIcon={!loading ? <LogIn size={16} /> : undefined}
        >
          {loading ? "Входим…" : "Войти"}
        </Button>

        <p className="text-center text-xs muted">
          Входя в аккаунт, вы соглашаетесь с правилами сервиса.
        </p>
      </motion.form>
    </AuthShell>
  );
}
