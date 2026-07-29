import { useState, useEffect, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertCircle,
  BriefcaseBusiness,
  DollarSign,
  Clock,
  Phone,
  User,
  Tag,
  RefreshCw,
} from "lucide-react";
import { extractApiError } from "@/api/client";
import {
  EmployerRoleRequiredError,
  vacanciesApi,
} from "@/api/vacancies";
import { categoriesApi } from "@/api/categories";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/Button";
import Input from "@/components/Input";
import AddressAutocomplete from "@/components/AddressAutocomplete";
import MapPicker from "@/components/MapPicker";
import type { Category, VacancyFormData } from "@/types";

const DEFAULT_FORM: VacancyFormData = {
  title: "",
  description: "",
  category_id: null,
  address: "",
  salary_from: "",
  salary_to: "",
  salary_currency: "BYN",
  schedule_type: "",
  contact_name: "",
  contact_phone: "",
  exact_location_public: false,
  lat: null,
  lng: null,
};

const SCHEDULE_OPTIONS = [
  { value: "", label: "Не выбрано" },
  { value: "full_time", label: "Полный день" },
  { value: "part_time", label: "Сменный график" },
  { value: "flexible", label: "Гибкий график" },
  { value: "gig", label: "Подработка" },
];

const CURRENCY_OPTIONS = ["BYN", "USD", "EUR", "RUB"];

interface FieldError {
  field: string;
  message: string;
}

export default function VacancyCreatePage(): JSX.Element {
  const navigate = useNavigate();
  const [form, setForm] = useState<VacancyFormData>(DEFAULT_FORM);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [fieldErrors, setFieldErrors] = useState<FieldError[]>([]);

  const loadCategories = () => {
    setCategoriesLoading(true);
    setCategoriesError(null);
    categoriesApi
      .list()
      .then((cats) => {
        setCategories(cats);
        setCategoriesError(null);
      })
      .catch((err) => {
        setCategories([]);
        const msg = extractApiError(err);
        setCategoriesError(msg || "Не удалось загрузить категории");
      })
      .finally(() => setCategoriesLoading(false));
  };

  useEffect(() => {
    loadCategories();
  }, []);

  function updateField<K extends keyof VacancyFormData>(key: K, value: VacancyFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => prev.filter((e) => e.field !== key));
  }

  function handleAddressChange(address: string, lat?: number, lng?: number) {
    setForm((prev) => ({
      ...prev,
      address,
      lat: lat ?? prev.lat,
      lng: lng ?? prev.lng,
    }));
    setFieldErrors((prev) => prev.filter((e) => e.field !== "address"));
  }

  function handleMapPick(lat: number, lng: number, address: string) {
    setForm((prev) => ({ ...prev, lat, lng, address }));
    setFieldErrors((prev) => prev.filter((e) => e.field !== "address"));
  }

  function validate(): FieldError[] {
    const errors: FieldError[] = [];
    if (form.title.trim().length < 3) {
      errors.push({ field: "title", message: "Название должно быть не менее 3 символов" });
    }
    const from = form.salary_from ? Number(form.salary_from) : null;
    const to = form.salary_to ? Number(form.salary_to) : null;
    if (from != null && to != null && from > to) {
      errors.push({ field: "salary_to", message: "Максимальная зарплата не может быть меньше минимальной" });
    }
    if (from != null && from < 0) {
      errors.push({ field: "salary_from", message: "Зарплата не может быть отрицательной" });
    }
    return errors;
  }

  function isAddressEmpty(): boolean {
    return form.address.trim().length === 0 && form.lat == null && form.lng == null;
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const errors = validate();
    if (errors.length > 0) {
      setFieldErrors(errors);
      return;
    }

    // Если адрес не заполнен — confirm-диалог
    if (isAddressEmpty()) {
      const confirmed = window.confirm(
        "Без адреса вакансия не появится на карте. Продолжить?"
      );
      if (!confirmed) return;
    }

    setSaving(true);
    setError(null);
    setFieldErrors([]);
    try {
      const salary_from = form.salary_from ? Number(form.salary_from) : undefined;
      const salary_to = form.salary_to ? Number(form.salary_to) : undefined;
      const vacancy = await vacanciesApi.create({
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        category_id: form.category_id ?? undefined,
        address: form.address.trim() || undefined,
        salary_from,
        salary_to,
        salary_currency: form.salary_currency || "BYN",
        schedule_type: form.schedule_type || undefined,
        contact_phone: form.contact_phone.trim() || undefined,
        contact_name: form.contact_name.trim() || undefined,
        exact_location_public: form.exact_location_public,
      });
      navigate(`/vacancies/${vacancy.id}`);
    } catch (caught) {
      // Сохраняем специальный тип ошибки для EmployerRoleRequiredError
      if (caught instanceof EmployerRoleRequiredError) {
        setError(caught);
        setSaving(false);
        return;
      }
      // Пытаемся распарсить field-level ошибки из 422
      if (
        caught &&
        typeof caught === "object" &&
        "response" in caught &&
        (caught as { response?: { status?: number; data?: { detail?: string; fields?: Record<string, string> } } }).response?.status === 422
      ) {
        const fields = (caught as { response?: { data?: { fields?: Record<string, string> } } }).response?.data?.fields;
        if (fields) {
          const parsed = Object.entries(fields).map(([field, message]) => ({ field, message }));
          setFieldErrors(parsed);
          setError(new Error("Пожалуйста, исправьте ошибки в форме"));
          setSaving(false);
          return;
        }
      }
      // Показываем текст ошибки от сервера пользователю
      const message = extractApiError(caught);
      setError(new Error(message));
    } finally {
      setSaving(false);
    }
  }

  const getFieldError = (field: string): string | null =>
    fieldErrors.find((e) => e.field === field)?.message ?? null;

  return (
    <AuthShell title="Новая вакансия" subtitle="Заполните информацию о позиции. Адрес можно указать текстом или кликнуть по карте.">
      <form className="space-y-5" onSubmit={onSubmit} noValidate>
        {/* Название */}
        <Input
          label="Название вакансии *"
          name="title"
          value={form.title}
          onChange={(e) => updateField("title", e.target.value)}
          placeholder="Например, Frontend-разработчик"
          minLength={3}
          required
          error={getFieldError("title")}
        />

        {/* Описание */}
        <div>
          <label className="label" htmlFor="vacancy-description">Описание</label>
          <textarea
            id="vacancy-description"
            className="input min-h-28 resize-y py-3"
            value={form.description}
            onChange={(e) => updateField("description", e.target.value)}
            placeholder="Опишите требования, обязанности и условия..."
          />
        </div>

        {/* Категория */}
        <div>
          <label className="label" htmlFor="vacancy-category">
            <Tag size={12} className="inline mr-1" />
            Категория
          </label>
          {categoriesLoading ? (
            <div className="flex items-center gap-2 text-sm text-ink-500 py-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-ink-300 border-t-brand-500" />
              Загрузка категорий...
            </div>
          ) : categoriesError ? (
            <div>
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/5 dark:text-amber-400">
                <div className="flex items-start gap-2">
                  <AlertCircle size={16} className="mt-0.5 shrink-0" />
                  <span>{categoriesError}</span>
                </div>
                <button
                  type="button"
                  onClick={loadCategories}
                  className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-amber-700 hover:text-amber-900 dark:text-amber-300 dark:hover:text-amber-100 underline"
                >
                  <RefreshCw size={12} />
                  Повторить загрузку
                </button>
              </div>
              <div className="mt-2">
                <Input
                  type="number"
                  placeholder="ID категории (опционально)"
                  value={form.category_id ?? ""}
                  onChange={(e) => updateField("category_id", e.target.value ? Number(e.target.value) : null)}
                />
              </div>
            </div>
          ) : categories.length > 0 ? (
            <select
              id="vacancy-category"
              className="input"
              value={form.category_id ?? ""}
              onChange={(e) => updateField("category_id", e.target.value ? Number(e.target.value) : null)}
            >
              <option value="">Не выбрано</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          ) : (
            <p className="text-sm text-ink-500 py-2">Нет доступных категорий</p>
          )}
        </div>

        {/* Адрес + карта */}
        <div className="space-y-2">
          <label className="label">
            Адрес места работы (обязательно для карты)
          </label>
          <AddressAutocomplete
            value={form.address}
            onChange={handleAddressChange}
            error={getFieldError("address")}
          />
          <p className="text-xs text-ink-500 -mt-1">
            Укажите адрес, чтобы вакансия отображалась на карте. Можно ввести вручную или кликнуть по карте ниже.
          </p>
          <div className="rounded-xl overflow-hidden">
            <MapPicker
              lat={form.lat}
              lng={form.lng}
              onPick={handleMapPick}
            />
          </div>
          {form.lat != null && form.lng != null && (
            <p className="text-xs muted">
              Выбраны координаты: {form.lat.toFixed(6)}, {form.lng.toFixed(6)}
            </p>
          )}
          <label className="flex items-center gap-2 mt-1 cursor-pointer">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-ink-300 text-brand-600 focus:ring-brand-500"
              checked={form.exact_location_public}
              onChange={(e) => updateField("exact_location_public", e.target.checked)}
            />
            <span className="text-sm text-ink-700 dark:text-ink-300">
              Показывать точный адрес соискателям
            </span>
          </label>
        </div>

        {/* Зарплата */}
        <fieldset className="rounded-xl border border-ink-200 p-4 dark:border-ink-700">
          <legend className="flex items-center gap-1.5 px-1 text-sm font-medium text-ink-700 dark:text-ink-300">
            <DollarSign size={14} />
            Зарплата
          </legend>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-2">
            <Input
              label="От"
              type="number"
              placeholder="0"
              value={form.salary_from}
              onChange={(e) => updateField("salary_from", e.target.value)}
              min="0"
              error={getFieldError("salary_from")}
            />
            <Input
              label="До"
              type="number"
              placeholder="0"
              value={form.salary_to}
              onChange={(e) => updateField("salary_to", e.target.value)}
              min="0"
              error={getFieldError("salary_to")}
            />
            <div>
              <label className="label">Валюта</label>
              <select
                className="input"
                value={form.salary_currency}
                onChange={(e) => updateField("salary_currency", e.target.value)}
              >
                {CURRENCY_OPTIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>
        </fieldset>

        {/* График */}
        <div>
          <label className="label" htmlFor="vacancy-schedule">
            <Clock size={12} className="inline mr-1" />
            График работы
          </label>
          <select
            id="vacancy-schedule"
            className="input"
            value={form.schedule_type}
            onChange={(e) => updateField("schedule_type", e.target.value)}
          >
            {SCHEDULE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Контакты */}
        <fieldset className="rounded-xl border border-ink-200 p-4 dark:border-ink-700">
          <legend className="flex items-center gap-1.5 px-1 text-sm font-medium text-ink-700 dark:text-ink-300">
            <Phone size={14} />
            Контактная информация
          </legend>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
            <Input
              label="Контактное лицо"
              leftIcon={<User size={14} />}
              placeholder="Иван Иванов"
              value={form.contact_name}
              onChange={(e) => updateField("contact_name", e.target.value)}
            />
            <Input
              label="Телефон"
              leftIcon={<Phone size={14} />}
              type="tel"
              placeholder="+375 (29) 123-45-67"
              value={form.contact_phone}
              onChange={(e) => updateField("contact_phone", e.target.value)}
            />
          </div>
        </fieldset>

        {/* Ошибки */}
        {error && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/5 dark:text-red-400">
            <div className="flex items-start gap-2">
              <AlertCircle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
              <span>{error.message}</span>
            </div>
            {error instanceof EmployerRoleRequiredError && (
              <Link className="mt-2 inline-block font-medium underline" to={error.profilePath}>
                Сменить роль в профиле
              </Link>
            )}
          </div>
        )}

        <Button
          type="submit"
          fullWidth
          loading={saving}
          disabled={saving || form.title.trim().length < 3}
          leftIcon={<BriefcaseBusiness size={16} aria-hidden="true" />}
        >
          Опубликовать вакансию
        </Button>
      </form>
    </AuthShell>
  );
}
