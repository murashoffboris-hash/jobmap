import { describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";
import { applicationsApi } from "./applications";
import type { Application, ApplicationListResponse } from "@/types";

vi.mock("./client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const mockApp: Application = {
  id: 1,
  user_id: 42,
  vacancy_id: 10,
  cover_letter: "Очень хочу у вас работать",
  status: "pending",
  vacancy_title: "Frontend-разработчик",
  employer_name: "ООО ТехноПлюс",
  applicant_name: "Иван Иванов",
  created_at: "2026-07-27T10:00:00Z",
  updated_at: "2026-07-27T10:00:00Z",
};

const mockList: ApplicationListResponse = {
  items: [mockApp],
  total: 1,
  page: 1,
  page_size: 10,
};

describe("applicationsApi", () => {
  describe("create", () => {
    it("отправляет POST /applications с vacancy_id", async () => {
      vi.mocked(apiClient.post).mockResolvedValue({ data: mockApp, status: 201, statusText: "Created", headers: {}, config: {} as any });
      const result = await applicationsApi.create({ vacancy_id: 10, cover_letter: "Тест" });
      expect(apiClient.post).toHaveBeenCalledWith("/applications", { vacancy_id: 10, cover_letter: "Тест" });
      expect(result).toEqual(mockApp);
    });
  });

  describe("listMy", () => {
    it("запрашивает GET /applications с пагинацией", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockList, status: 200, statusText: "OK", headers: {}, config: {} as any });
      const result = await applicationsApi.listMy({ page: 1, page_size: 10 });
      expect(apiClient.get).toHaveBeenCalledWith("/applications", { params: { page: 1, page_size: 10 } });
      expect(result).toEqual(mockList);
    });
  });

  describe("withdraw", () => {
    it("отправляет PATCH /applications/{id}/withdraw", async () => {
      const withdrawn = { ...mockApp, status: "withdrawn" as const };
      vi.mocked(apiClient.patch).mockResolvedValue({ data: withdrawn, status: 200, statusText: "OK", headers: {}, config: {} as any });
      const result = await applicationsApi.withdraw(1);
      expect(apiClient.patch).toHaveBeenCalledWith("/applications/1/withdraw");
      expect(result.status).toBe("withdrawn");
    });
  });

  describe("updateStatus", () => {
    it("отправляет PATCH /applications/{id}/status с новым статусом", async () => {
      const accepted = { ...mockApp, status: "accepted" as const };
      vi.mocked(apiClient.patch).mockResolvedValue({ data: accepted, status: 200, statusText: "OK", headers: {}, config: {} as any });
      const result = await applicationsApi.updateStatus(1, { status: "accepted" });
      expect(apiClient.patch).toHaveBeenCalledWith("/applications/1/status", { status: "accepted" });
      expect(result.status).toBe("accepted");
    });
  });

  describe("listByVacancy", () => {
    it("запрашивает GET /vacancies/{id}/applications", async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockList, status: 200, statusText: "OK", headers: {}, config: {} as any });
      const result = await applicationsApi.listByVacancy(10, { page: 1, page_size: 20 });
      expect(apiClient.get).toHaveBeenCalledWith("/vacancies/10/applications", { params: { page: 1, page_size: 20 } });
      expect(result.items).toHaveLength(1);
    });
  });
});
