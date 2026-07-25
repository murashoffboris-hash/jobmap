import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, BriefcaseBusiness } from "lucide-react";
import { extractApiError } from "@/api/client";
import {
  EmployerRoleRequiredError,
  vacanciesApi,
} from "@/api/vacancies";
import AuthShell from "@/components/AuthShell";
import Button from "@/components/Button";
import Input from "@/components/Input";

export default function VacancyCreatePage(): JSX.Element {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [address, setAddress] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const vacancy = await vacanciesApi.create({
        title: title.trim(),
        ...(description.trim() && { description: description.trim() }),
        ...(address.trim() && { address: address.trim() }),
      });
      navigate(`/vacancies/${vacancy.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught : new Error(extractApiError(caught)));
    } finally {
      setSaving(false);
    }
  }

  return (
    <AuthShell title="Новая вакансия" subtitle="Опишите позицию и опубликуйте её на JobMap.">
      <form className="space-y-4" onSubmit={onSubmit}>
        <Input
          label="Название вакансии"
          name="title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          minLength={3}
          required
        />
        <div>
          <label className="label" htmlFor="vacancy-description">Описание</label>
          <textarea
            id="vacancy-description"
            className="input min-h-28 resize-y py-3"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
          />
        </div>
        <Input label="Адрес" value={address} onChange={(event) => setAddress(event.target.value)} />

        {error && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
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

        <Button type="submit" fullWidth loading={saving} disabled={saving || title.trim().length < 3}
          leftIcon={<BriefcaseBusiness size={16} aria-hidden="true" />}>
          Опубликовать вакансию
        </Button>
      </form>
    </AuthShell>
  );
}
