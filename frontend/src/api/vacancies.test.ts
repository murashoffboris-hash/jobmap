import { describe, expect, it, vi } from "vitest";
import { AxiosError, AxiosHeaders } from "axios";
import { apiClient } from "./client";
import { EmployerRoleRequiredError, vacanciesApi } from "./vacancies";
import type { VacancyCreateRequest } from "@/types";

vi.mock("./client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

const request: VacancyCreateRequest = {
  title: "Frontend-разработчик",
  description: "React и TypeScript",
  address: "Минск",
};

describe("vacanciesApi.create", () => {
  it("преобразует 403 Employer or admin role required в понятную ошибку роли", async () => {
    const error = new AxiosError(
      "Forbidden",
      "ERR_BAD_REQUEST",
      { headers: new AxiosHeaders() },
      undefined,
      {
        status: 403,
        statusText: "Forbidden",
        headers: {},
        config: { headers: new AxiosHeaders() },
        data: { detail: "Employer or admin role required" },
      },
    );
    vi.mocked(apiClient.post).mockRejectedValue(error);

    await expect(vacanciesApi.create(request)).rejects.toBeInstanceOf(EmployerRoleRequiredError);
  });
});
