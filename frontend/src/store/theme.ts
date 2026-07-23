import { create } from "zustand";

export type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  toggle: () => void;
  set: (t: Theme) => void;
}

const STORAGE_KEY = "jobmap.theme";

function detectInitial(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* localStorage недоступен — фоллбек ниже */
  }
  const prefersDark =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  if (theme === "dark") root.classList.add("dark");
  else root.classList.remove("dark");
  // Подсветка адресной строки в PWA
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", theme === "dark" ? "#020617" : "#f8fafc");
  }
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* silent */
  }
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  theme: detectInitial(),

  toggle(): void {
    const next: Theme = get().theme === "dark" ? "light" : "dark";
    applyTheme(next);
    set({ theme: next });
  },

  set(t: Theme): void {
    applyTheme(t);
    set({ theme: t });
  },
}));

/** Применить текущую тему к <html> (вызывается один раз на старте). */
export function initTheme(): void {
  applyTheme(useThemeStore.getState().theme);
}
