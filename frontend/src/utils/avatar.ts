/**
 * Инициалы для аватарки: первая буква имени + первая буква фамилии.
 * Если name пуст — fallback на email (первые 2 символа).
 * Если и email пуст — ?. Поддерживает кириллицу.
 */
export function getInitials(name: string | null | undefined, email?: string | null): string {
  const src = (name ?? "").trim();
  if (src) {
    const parts = src.split(/\s+/).filter(Boolean);
    if (parts.length === 1) {
      return parts[0]!.slice(0, 2).toUpperCase();
    }
    return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase();
  }
  if (email) {
    const local = email.split("@")[0] ?? "";
    return local.slice(0, 2).toUpperCase() || "?";
  }
  return "?";
}

/** Детерминированный цвет аватарки на основе строки (имя/email). */
export function getAvatarColor(seed: string): string {
  const palette = [
    "from-violet-500 to-indigo-500",
    "from-sky-500 to-cyan-500",
    "from-emerald-500 to-teal-500",
    "from-rose-500 to-pink-500",
    "from-amber-500 to-orange-500",
    "from-fuchsia-500 to-purple-500",
  ];
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return palette[hash % palette.length]!;
}
