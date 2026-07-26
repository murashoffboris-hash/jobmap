import { type FormEvent, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertCircle,
  AtSign,
  CheckCircle2,
  Edit3,
  Mail,
  Phone,
  Save,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react";
import { authApi } from "@/api/auth";
import { extractApiError } from "@/api/client";
import Avatar from "@/components/Avatar";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/Button";
import Input from "@/components/Input";
import { useAuthStore } from "@/store/auth";
import type { RegistrationRole, UpdateProfileRequest, User } from "@/types";

interface ProfileForm {
  full_name: string;
  phone: string;
  bio: string;
}

interface FormErrors {
  full_name?: string;
  phone?: string;
  bio?: string;
}

const PHONE_PATTERN = /^\+?[0-9()\s-]{7,32}$/;

function formFromUser(user: User): ProfileForm {
  return {
    full_name: user.full_name ?? "",
    phone: user.phone ?? "",
    bio: user.bio ?? "",
  };
}

function trimOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
}

export default function ProfilePage(): JSX.Element {
  const user = useAuthStore((state) => state.user);
  const updateUser = useAuthStore((state) => state.updateUser);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<ProfileForm>(() =>
    user ? formFromUser(user) : { full_name: "", phone: "", bio: "" },
  );
  const [errors, setErrors] = useState<FormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [roleSaving, setRoleSaving] = useState(false);

  if (!user) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm muted">
        Данные профиля недоступны
      </div>
    );
  }

  return (
    <ProfileContent
      user={user}
      editing={editing}
      saving={saving}
      form={form}
      errors={errors}
      formError={formError}
      successMessage={successMessage}
      roleSaving={roleSaving}
      setForm={setForm}
      onEdit={() => {
        setForm(formFromUser(user));
        setErrors({});
        setFormError(null);
        setSuccessMessage(null);
        setEditing(true);
      }}
      onCancel={() => {
        setForm(formFromUser(user));
        setErrors({});
        setFormError(null);
        setEditing(false);
      }}
      onSubmit={async (event) => {
        event.preventDefault();
        setFormError(null);
        setSuccessMessage(null);

        const nextErrors = validateProfile(form);
        setErrors(nextErrors);
        if (Object.keys(nextErrors).length > 0) return;

        const request: UpdateProfileRequest = {
          full_name: form.full_name.trim(),
          phone: trimOrNull(form.phone),
          bio: trimOrNull(form.bio),
        };

        setSaving(true);
        try {
          const updatedUser = await authApi.updateProfile(request);
          updateUser(updatedUser);
          setForm(formFromUser(updatedUser));
          setEditing(false);
          setSuccessMessage("Профиль сохранён");
        } catch (error) {
          setFormError(extractApiError(error) || "Не удалось сохранить профиль");
        } finally {
          setSaving(false);
        }
      }}
      onRoleChange={async (role) => {
        if (role === user.role) return;
        const confirmed = window.confirm(
          role === "employer"
            ? "Переключиться на роль работодателя? Вы сможете создавать вакансии."
            : "Переключиться на роль соискателя?",
        );
        if (!confirmed) return;

        setRoleSaving(true);
        setFormError(null);
        setSuccessMessage(null);
        try {
          const updatedUser = await authApi.updateRole(role);
          updateUser(updatedUser);
          setSuccessMessage(`Роль изменена: ${roleLabel(updatedUser.role)}`);
        } catch (error) {
          setFormError(extractApiError(error) || "Не удалось изменить роль");
        } finally {
          setRoleSaving(false);
        }
      }}
    />
  );
}

function validateProfile(form: ProfileForm): FormErrors {
  const errors: FormErrors = {};
  const fullName = form.full_name.trim();
  const phone = form.phone.trim();
  const bio = form.bio.trim();

  if (!fullName) {
    errors.full_name = "Укажите имя и фамилию";
  } else if (fullName.length > 255) {
    errors.full_name = "Имя не должно быть длиннее 255 символов";
  }

  if (phone && !PHONE_PATTERN.test(phone)) {
    errors.phone = "Введите телефон в международном формате";
  }

  if (bio.length > 1_000) {
    errors.bio = "Описание не должно быть длиннее 1000 символов";
  }

  return errors;
}

interface ProfileContentProps {
  user: User;
  editing: boolean;
  saving: boolean;
  form: ProfileForm;
  errors: FormErrors;
  formError: string | null;
  successMessage: string | null;
  roleSaving: boolean;
  setForm: React.Dispatch<React.SetStateAction<ProfileForm>>;
  onEdit: () => void;
  onCancel: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => Promise<void>;
  onRoleChange: (role: RegistrationRole) => Promise<void>;
}

function ProfileContent({
  user,
  editing,
  saving,
  form,
  errors,
  formError,
  successMessage,
  roleSaving,
  setForm,
  onEdit,
  onCancel,
  onSubmit,
  onRoleChange,
}: ProfileContentProps): JSX.Element {
  const displayName = user.full_name?.trim() || user.email.split("@")[0] || "Пользователь";

  return (
    <AuthShell
      title="Личный профиль"
      subtitle="Контактные данные помогают работодателям и соискателям быстрее связаться с вами."
    >
      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        aria-label="Профиль пользователя"
      >
        <div className="flex flex-col items-center text-center">
          <div className="rounded-full bg-gradient-to-br from-brand-200 to-sky-200 p-1 shadow-soft dark:from-brand-500/40 dark:to-sky-500/30">
            <Avatar name={user.full_name} email={user.email} size="lg" className="h-24 w-24 text-2xl" />
          </div>
          <h1 className="mt-4 text-xl font-semibold text-ink-900 dark:text-ink-50">
            {displayName}
          </h1>
          <span className="chip mt-2">{roleLabel(user.role)}</span>
        </div>

        {successMessage && (
          <div
            role="status"
            className="mt-5 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-sm text-emerald-700 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300"
          >
            <CheckCircle2 size={16} aria-hidden="true" />
            <span>{successMessage}</span>
          </div>
        )}

        {editing ? (
          <form className="mt-6 space-y-4" onSubmit={onSubmit} noValidate>
            <Input
              label="Имя и фамилия"
              name="full_name"
              autoComplete="name"
              maxLength={255}
              value={form.full_name}
              onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
              leftIcon={<UserRound size={16} aria-hidden="true" />}
              error={errors.full_name}
              disabled={saving}
              required
            />
            <Input
              label="Телефон"
              name="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              maxLength={32}
              placeholder="+375 29 123-45-67"
              value={form.phone}
              onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
              leftIcon={<Phone size={16} aria-hidden="true" />}
              error={errors.phone}
              disabled={saving}
            />
            <div className="w-full">
              <label htmlFor="bio" className="label">
                О себе
              </label>
              <textarea
                id="bio"
                name="bio"
                rows={5}
                maxLength={1_000}
                value={form.bio}
                onChange={(event) => setForm((current) => ({ ...current, bio: event.target.value }))}
                disabled={saving}
                aria-invalid={errors.bio ? true : undefined}
                className="input min-h-28 resize-y py-3"
                placeholder="Расскажите об опыте, навыках и желаемой работе"
              />
              <div className="mt-1.5 flex items-start justify-between gap-3 text-xs">
                <span className={errors.bio ? "text-red-600 dark:text-red-400" : "muted"}>
                  {errors.bio ?? "Необязательное поле"}
                </span>
                <span className="shrink-0 muted">{form.bio.length}/1000</span>
              </div>
            </div>

            {formError && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300"
              >
                <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
                <span>{formError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 pt-2 sm:grid-cols-2">
              <Button
                type="submit"
                loading={saving}
                leftIcon={<Save size={16} aria-hidden="true" />}
                fullWidth
              >
                Сохранить
              </Button>
              <Button
                type="button"
                variant="outline"
                leftIcon={<X size={16} aria-hidden="true" />}
                onClick={onCancel}
                disabled={saving}
                fullWidth
              >
                Отмена
              </Button>
            </div>
          </form>
        ) : (
          <div className="mt-6 space-y-4">
            <ProfileField
              icon={<Mail size={17} aria-hidden="true" />}
              label="Email"
              value={user.email}
            />
            <ProfileField
              icon={<Phone size={17} aria-hidden="true" />}
              label="Телефон"
              value={user.phone?.trim() || "Не указан"}
              muted={!user.phone?.trim()}
            />
            <ProfileField
              icon={<AtSign size={17} aria-hidden="true" />}
              label="О себе"
              value={user.bio?.trim() || "Добавьте несколько слов о себе"}
              muted={!user.bio?.trim()}
              multiline
            />
            {(user.role === "user" || user.role === "employer") && (
              <div className="rounded-xl border border-ink-200/70 bg-ink-50/70 px-4 py-3 dark:border-ink-800 dark:bg-ink-950/30">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-ink-500 dark:text-ink-400">
                  <ShieldCheck size={17} className="text-brand-600 dark:text-brand-300" aria-hidden="true" />
                  <span>Роль аккаунта</span>
                </div>
                <p className="mt-1.5 text-sm text-ink-700 dark:text-ink-200">
                  {user.role === "employer"
                    ? "Вы можете публиковать вакансии."
                    : "Переключитесь на работодателя, чтобы публиковать вакансии."}
                </p>
                <Button
                  type="button"
                  variant="outline"
                  fullWidth
                  loading={roleSaving}
                  disabled={roleSaving}
                  onClick={() => onRoleChange(user.role === "employer" ? "user" : "employer")}
                  className="mt-3"
                >
                  {user.role === "employer" ? "Стать соискателем" : "Стать работодателем"}
                </Button>
              </div>
            )}
            <Button
              variant="primary"
              size="lg"
              fullWidth
              leftIcon={<Edit3 size={16} aria-hidden="true" />}
              onClick={onEdit}
              className="mt-2"
            >
              Редактировать
            </Button>
          </div>
        )}
      </motion.section>
    </AuthShell>
  );
}

interface ProfileFieldProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  muted?: boolean;
  multiline?: boolean;
}

function ProfileField({ icon, label, value, muted = false, multiline = false }: ProfileFieldProps): JSX.Element {
  return (
    <div className="rounded-xl border border-ink-200/70 bg-ink-50/70 px-4 py-3 dark:border-ink-800 dark:bg-ink-950/30">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-ink-500 dark:text-ink-400">
        <span className="text-brand-600 dark:text-brand-300">{icon}</span>
        <span>{label}</span>
      </div>
      <p
        className={`mt-1.5 text-sm ${multiline ? "whitespace-pre-wrap" : "break-all"} ${
          muted ? "text-ink-400 dark:text-ink-500" : "text-ink-800 dark:text-ink-100"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function roleLabel(role: User["role"]): string {
  switch (role) {
    case "user":
      return "Соискатель";
    case "employer":
      return "Работодатель";
    case "admin":
      return "Администратор";
    case "moderator":
      return "Модератор";
    default:
      return role;
  }
}
