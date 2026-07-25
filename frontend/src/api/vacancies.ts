import axios from "axios";
import { apiClient } from "./client";
import type { Vacancy, VacancyCreateRequest, VacancyListResponse } from "@/types";

export const EMPLOYER_ROLE_REQUIRED_MESSAGE =
  "Создавать вакансии может только работодатель. Сменить роль можно в профиле";

export class EmployerRoleRequiredError extends Error {
  readonly profilePath = "/profile";

  constructor() {
    super(EMPLOYER_ROLE_REQUIRED_MESSAGE);
    this.name = "EmployerRoleRequiredError";
  }
}

export interface VacancyListParams {
  page?: number;
  page_size?: number;
  city?: string;
  employment_type?: string;
  search?: string;
  bbox?: [number, number, number, number]; // [west, south, east, north]
}

export const vacanciesApi = {
  async list(params: VacancyListParams = {}): Promise<VacancyListResponse> {
    const res = await apiClient.get<VacancyListResponse>("/vacancies", { params });
    return res.data;
  },

  async get(id: number): Promise<Vacancy> {
    const res = await apiClient.get<Vacancy>(`/vacancies/${id}`);
    return res.data;
  },

  async create(data: VacancyCreateRequest): Promise<Vacancy> {
    try {
      const res = await apiClient.post<Vacancy>("/vacancies", data);
      return res.data;
    } catch (error) {
      if (
        axios.isAxiosError<{ detail?: string }>(error) &&
        error.response?.status === 403 &&
        error.response.data?.detail === "Employer or admin role required"
      ) {
        throw new EmployerRoleRequiredError();
      }
      throw error;
    }
  },
};
