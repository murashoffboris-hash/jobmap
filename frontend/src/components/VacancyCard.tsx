import { Link } from "react-router-dom";
import type { Vacancy } from "@/types";
import { formatEmploymentType, formatSalary } from "@/utils/format";

export interface VacancyCardProps {
  vacancy: Vacancy;
}

export default function VacancyCard({ vacancy }: VacancyCardProps): JSX.Element {
  return (
    <Link to={`/vacancies/${vacancy.id}`} className="card" style={{ display: "block" }}>
      <p className="vacancy-title">{vacancy.title}</p>
      <p className="vacancy-meta">
        {vacancy.employer_name ?? "Работодатель"} · {vacancy.city ?? "город не указан"}
      </p>
      <p className="vacancy-meta">
        {formatSalary(vacancy.salary_from, vacancy.salary_to, vacancy.currency)} ·{" "}
        {formatEmploymentType(vacancy.employment_type)}
      </p>
    </Link>
  );
}
