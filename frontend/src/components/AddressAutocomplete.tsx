import { useState, useEffect, useRef, useCallback } from "react";
import { MapPin } from "lucide-react";
import { geoApi } from "@/api/geo";
import type { GeocodeResult } from "@/types";

interface AddressAutocompleteProps {
  value: string;
  onChange: (address: string, lat?: number, lng?: number) => void;
  error?: string | null;
  required?: boolean;
}

export default function AddressAutocomplete({
  value,
  onChange,
  error,
  required,
}: AddressAutocompleteProps): JSX.Element {
  const [suggestions, setSuggestions] = useState<GeocodeResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const selectedRef = useRef(false);

  // Sync external value changes (e.g. from map picker reverse geocode)
  useEffect(() => {
    if (!selectedRef.current) {
      setInputValue(value);
    }
    selectedRef.current = false;
  }, [value]);

  const fetchSuggestions = useCallback(async (query: string) => {
    if (query.trim().length < 2) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    setLoading(true);
    try {
      const results = await geoApi.geocode(query.trim());
      setSuggestions(results.filter((r) => r.display_name));
      setOpen(true);
    } catch {
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(val), 300);
  };

  const handleSelect = (result: GeocodeResult) => {
    selectedRef.current = true;
    const addr = result.display_name ?? "";
    setInputValue(addr);
    setSuggestions([]);
    setOpen(false);
    onChange(addr, result.lat ?? undefined, result.lon ?? undefined);
  };

  // Close dropdown on outside click
  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400">
          <MapPin size={16} />
        </span>
        <input
          type="text"
          className={`input pl-10 pr-8 ${error ? "border-red-400 focus:border-red-500 focus:ring-red-400/30" : ""}`}
          placeholder="Начните вводить адрес..."
          value={inputValue}
          onChange={handleInputChange}
          onFocus={() => {
            if (suggestions.length > 0) setOpen(true);
          }}
          required={required}
          aria-label="Адрес места работы"
          aria-invalid={error ? true : undefined}
        />
        {loading && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2">
            <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-300 border-t-brand-500" />
          </span>
        )}
      </div>
      {error && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{error}</p>}

      {open && suggestions.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-50 mt-1 w-full overflow-hidden rounded-xl border border-ink-200 bg-white shadow-xl dark:border-ink-700 dark:bg-ink-900"
        >
          {suggestions.map((s, i) => (
            <li
              key={s.osm_id ?? i}
              role="option"
              aria-selected={false}
              className="flex cursor-pointer items-start gap-2 px-3.5 py-2.5 text-sm text-ink-700 transition-colors hover:bg-ink-50 dark:text-ink-200 dark:hover:bg-ink-800"
              onClick={() => handleSelect(s)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSelect(s);
              }}
              tabIndex={0}
            >
              <MapPin size={14} className="mt-0.5 shrink-0 text-ink-400" />
              <span className="line-clamp-2">{s.display_name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
