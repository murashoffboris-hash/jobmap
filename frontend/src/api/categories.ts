import { apiClient } from "./client";
import type { Category } from "@/types";

export const categoriesApi = {
  async list(): Promise<Category[]> {
    const res = await apiClient.get<Category[]>("/categories");
    return res.data;
  },
};
