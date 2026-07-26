import { apiClient } from "./client";
import type { Category } from "@/types";

export const categoriesApi = {
  async list(): Promise<Category[]> {
    try {
      const res = await apiClient.get<Category[]>("/categories");
      return res.data;
    } catch {
      // Категории пока недоступны — возвращаем пустой массив
      return [];
    }
  },
};
