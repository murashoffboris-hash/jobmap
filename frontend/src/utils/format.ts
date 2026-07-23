export function formatSalary(from: number | null, to: number | null, currency: string): string {
  if (from == null && to == null) return "з/п не указана";
  const fmt = (n: number) => new Intl.NumberFormat("ru-RU").format(n);
  if (from != null && to != null) return `${fmt(from)}–${fmt(to)} ${currency}`;
  if (from != null) return `от ${fmt(from)} ${currency}`;
  return `до ${fmt(to as number)} ${currency}`;
}

export function formatEmploymentType(t: string): string {
  const map: Record<string, string> = {
    full_time: "Полная занятость",
    part_time: "Частичная",
    contract: "Договор подряда",
    internship: "Стажировка",
    gig: "Разовая / подработка",
  };
  return map[t] ?? t;
}

export function parseCenter(envValue: string | undefined): [number, number] {
  if (!envValue) return [27.5615, 53.9045]; // Минск по умолчанию
  try {
    const parsed = JSON.parse(envValue);
    if (Array.isArray(parsed) && parsed.length === 2) {
      return [Number(parsed[0]), Number(parsed[1])];
    }
  } catch {
    // fallthrough
  }
  return [27.5615, 53.9045];
}

export function parseZoom(envValue: string | undefined): number {
  const n = Number(envValue);
  return Number.isFinite(n) && n > 0 ? n : 11;
}
