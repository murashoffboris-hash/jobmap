import { apiClient } from "./client";
import type { Vacancy, VacancyListResponse } from "@/types";

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
};
