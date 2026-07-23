import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Утилита склейки CSS-классов с поддержкой Tailwind merge:
 * повторяющиеся утилиты (например `px-2 px-4`) автоматически схлопываются.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
