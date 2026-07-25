// Доменные типы JobMap — отражают backend/app/schemas.py.
// Держим минимальный набор для MVP-фронта; расширяем по мере роста API.

export type UserRole = "user" | "employer" | "admin" | "moderator";
export type RegistrationRole = "user" | "employer";
export type RegistrationUiRole = "worker" | "employer";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  phone: string | null;
  bio: string | null;
  avatar_url: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface UpdateProfileRequest {
  full_name: string;
  phone: string | null;
  bio: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  role: RegistrationRole;
}

export interface UpdateRoleRequest {
  role: RegistrationRole;
}

export type EmploymentType = "full_time" | "part_time" | "contract" | "internship" | "gig";

export interface Vacancy {
  id: number;
  title: string;
  description: string;
  salary_from: number | null;
  salary_to: number | null;
  currency: string;
  employment_type: EmploymentType;
  employer_id: number;
  employer_name: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VacancyListResponse {
  items: Vacancy[];
  total: number;
  page: number;
  page_size: number;
}

export interface VacancyCreateRequest {
  title: string;
  description?: string;
  category_id?: number;
  address?: string;
  salary_from?: number;
  salary_to?: number;
  salary_currency?: string;
  schedule_type?: string;
  contact_phone?: string;
  contact_name?: string;
  exact_location_public?: boolean;
}

export interface ApiError {
  detail: string;
  code?: string;
  fields?: Record<string, string>;
}

export interface MapPoint {
  id: number;
  lat: number;
  lng: number;
  title: string;
  payload?: Record<string, unknown>;
}
