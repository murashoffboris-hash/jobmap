import { apiClient } from "./client";
import type {
  Application,
  ApplicationCreateRequest,
  ApplicationListResponse,
  ApplicationStatusUpdateRequest,
} from "@/types";

export interface ApplicationListParams {
  page?: number;
  page_size?: number;
}

export const applicationsApi = {
  /** Создать отклик на вакансию — POST /api/applications */
  async create(data: ApplicationCreateRequest): Promise<Application> {
    const res = await apiClient.post<Application>("/applications", data);
    return res.data;
  },

  /** Мои отклики (пагинированный список) — GET /api/applications */
  async listMy(params: ApplicationListParams = {}): Promise<ApplicationListResponse> {
    const res = await apiClient.get<ApplicationListResponse>("/applications", { params });
    return res.data;
  },

  /** Отозвать отклик — PATCH /api/applications/{id}/withdraw */
  async withdraw(applicationId: number): Promise<Application> {
    const res = await apiClient.patch<Application>(
      `/applications/${applicationId}/withdraw`
    );
    return res.data;
  },

  /** Изменить статус отклика (принять/отклонить) — PATCH /api/applications/{id}/status */
  async updateStatus(
    applicationId: number,
    data: ApplicationStatusUpdateRequest
  ): Promise<Application> {
    const res = await apiClient.patch<Application>(
      `/applications/${applicationId}/status`,
      data
    );
    return res.data;
  },

  /** Отклики на конкретную вакансию (для работодателя) — GET /api/vacancies/{id}/applications */
  async listByVacancy(
    vacancyId: number,
    params: ApplicationListParams = {}
  ): Promise<ApplicationListResponse> {
    const res = await apiClient.get<ApplicationListResponse>(
      `/vacancies/${vacancyId}/applications`,
      { params }
    );
    return res.data;
  },
};
