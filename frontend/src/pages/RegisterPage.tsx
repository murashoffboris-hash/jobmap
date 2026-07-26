import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Mail, Lock, User as UserIcon, AlertCircle, UserPlus, Briefcase, Search } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import { extractApiError } from "@/api/client";
import { toRegistrationRole } from "@/api/auth";
import type { RegistrationUiRole } from "@/types";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/Button";
import Input from "@/components/Input";
import { cn } from "@/utils/cn";

export default function RegisterPage(): JSX.Element {
  const navigate = useNavigate();

  const register = useAuthStore((s) => s.register);
  const status = useAuthStore((s) => s.status);
  const clearError = useAuthStore((s) => s.clearError);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [role, setRole] = useState<RegistrationUiRole>("worker");

  const [nameError, setNameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  function validate(): boolean {
    let ok = true;
    setNameError(null);
    setEmailError(null);
    setPasswordError(null);
    setConfirmError(null);
    setFormError(null);

    const trimmedName = name.trim();
    if (!trimmedName) {
      setNameError("Укажите имя");
      ok = false;
    } else if (trimmedName.length < 2) {
      setNameError("Имя слишком короткое");
      ok = false;
    }

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setEmailError("Введите email");
      ok = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      setEmailError("Похоже на некорректный email");
      ok = false;
    }

    if (!password) {
      setPasswordError("Придумайте пароль");
      ok = false;
    } else if (password.length < 6) {
      setPasswordError("Пароль должен быть не короче 6 символов");
      ok = false;
    }

    if (!confirm) {
      setConfirmError("Повторите пароль");
      ok = false;
    } else if (confirm !== password) {
      setConfirmError("Пароли не совпадают");
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
      // В сторе после register идёт авто-логин → нас перекинет на главную.
      await register({
        email: email.trim(),
        password,
        full_name: name.trim(),
        role: toRegistrationRole(role),
      });
      const registeredUser = useAuthStore.getState().user;
      const expectedRole = toRegistrationRole(role);
      if (registeredUser?.role !== expectedRole) {
        setFormError(
          "Аккаунт создан, но сервер не сохранил выбранную роль. Проверьте роль в профиле перед продолжением.",
        );
        return;
      }
      navigate("/", { replace: true });
    } catch (err) {
      setFormError(extractApiError(err) || "Не удалось зарегистрироваться");
    }
  }

  const loading = status === "loading";

  return (
    <AuthShell
      title="Создайте аккаунт"
      subtitle="Это займёт меньше минуты. Можно войти через соцсети позже."
      footer={
        <span className="muted">
          Уже есть аккаунт?{" "}
          <Link to="/login" className="font-medium text-brand-700 hover:underline dark:text-brand-300">
            Войти
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
        {/* Переключатель роли — две большие плитки */}
        <div>
          <span className="label">Я ищу…</span>
          <div className="grid grid-cols-2 gap-3">
            <RoleTile
              active={role === "worker"}
              onClick={() => setRole("worker")}
              icon={<Search size={18} />}
              title="Работу"
              desc="Откликаюсь на вакансии"
              disabled={loading}
            />
            <RoleTile
              active={role === "employer"}
              onClick={() => setRole("employer")}
              icon={<Briefcase size={18} />}
              title="Сотрудников"
              desc="Публикую вакансии"
              disabled={loading}
            />
          </div>
        </div>

        <Input
          label="Имя"
          name="full_name"
          autoComplete="name"
          placeholder="Иван Иванов"
          value={name}
          onChange={(e) => setName(e.target.value)}
          leftIcon={<UserIcon size={16} />}
          error={nameError}
          disabled={loading}
          required
        />

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
          autoComplete="new-password"
          placeholder="Не менее 6 символов"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          leftIcon={<Lock size={16} />}
          error={passwordError}
          hint="Минимум 6 символов. Используйте буквы разного регистра и цифры."
          disabled={loading}
          required
        />

        <Input
          label="Повторите пароль"
          type="password"
          name="confirm"
          autoComplete="new-password"
          placeholder="Ещё раз"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          leftIcon={<Lock size={16} />}
          error={confirmError}
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
          leftIcon={!loading ? <UserPlus size={16} /> : undefined}
        >
          {loading ? "Создаём…" : "Зарегистрироваться"}
        </Button>
      </motion.form>
    </AuthShell>
  );
}

interface RoleTileProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  desc: string;
  disabled?: boolean;
}
function RoleTile({
  active,
  onClick,
  icon,
  title,
  desc,
  disabled,
}: RoleTileProps): JSX.Element {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2",
        "focus-visible:ring-offset-white dark:focus-visible:ring-offset-ink-950",
        active
          ? "border-brand-500 bg-brand-50 text-brand-800 shadow-glow dark:border-brand-400 dark:bg-brand-500/10 dark:text-brand-200"
          : "border-ink-200 bg-white text-ink-700 hover:border-ink-300 hover:bg-ink-50 dark:border-ink-700 dark:bg-ink-900 dark:text-ink-200 dark:hover:border-ink-600 dark:hover:bg-ink-800",
        disabled && "opacity-60",
      )}
      aria-pressed={active}
    >
      <span
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg",
          active
            ? "bg-brand-600 text-white"
            : "bg-ink-100 text-ink-600 dark:bg-ink-800 dark:text-ink-300",
        )}
      >
        {icon}
      </span>
      <span className="text-sm font-semibold">{title}</span>
      <span className="text-xs muted">{desc}</span>
    </button>
  );
}
