import { useEffect, useRef, useCallback } from "react";
import maplibregl, { type Map as MapLibreMap, type Marker } from "maplibre-gl";
import { geoApi } from "@/api/geo";
import { parseCenter, parseZoom } from "@/utils/format";

interface MapPickerProps {
  lat: number | null;
  lng: number | null;
  onPick: (lat: number, lng: number, address: string) => void;
}

/**
 * Мини-карта для выбора точки на карте.
 * Клик → маркер → reverse geocode → подстановка адреса в поле.
 */
export default function MapPicker({ lat, lng, onPick }: MapPickerProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const onPickRef = useRef(onPick);

  onPickRef.current = onPick;

  const styleUrl =
    import.meta.env.VITE_MAP_STYLE_URL ??
    "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";
  const center = parseCenter(import.meta.env.VITE_MAP_DEFAULT_CENTER) ?? [27.5618, 53.9045]; // Минск
  const zoom = parseZoom(import.meta.env.VITE_MAP_DEFAULT_ZOOM) ?? 11;

  const updateMarker = useCallback((map: MapLibreMap, newLat: number, newLng: number) => {
    if (markerRef.current) markerRef.current.remove();
    const el = document.createElement("div");
    el.style.width = "28px";
    el.style.height = "28px";
    el.style.borderRadius = "50%";
    el.style.background = "#6366f1";
    el.style.border = "3px solid white";
    el.style.boxShadow = "0 2px 8px rgba(0,0,0,0.3)";
    el.style.cursor = "pointer";
    const marker = new maplibregl.Marker({ element: el, draggable: false })
      .setLngLat([newLng, newLat])
      .addTo(map);
    markerRef.current = marker;
  }, []);

  // Init map
  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center: [lng ?? center[0], lat ?? center[1]],
      zoom: lat && lng ? 14 : zoom,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
    mapRef.current = map;

    // Клик по карте — ставим маркер и делаем reverse geocode
    map.on("click", async (e) => {
      const { lng: newLng, lat: newLat } = e.lngLat;
      updateMarker(map, newLat, newLng);
      try {
        const result = await geoApi.reverse(newLat, newLng);
        const addr = result.display_name ?? `${newLat.toFixed(6)}, ${newLng.toFixed(6)}`;
        onPickRef.current(newLat, newLng, addr);
      } catch {
        onPickRef.current(newLat, newLng, `${newLat.toFixed(6)}, ${newLng.toFixed(6)}`);
      }
    });

    return () => {
      if (markerRef.current) markerRef.current.remove();
      markerRef.current = null;
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Show/hide marker based on props
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (lat != null && lng != null && Number.isFinite(lat) && Number.isFinite(lng)) {
      updateMarker(map, lat, lng);
      map.flyTo({ center: [lng, lat], zoom: 14, duration: 800 });
    }
  }, [lat, lng, updateMarker]);

  return (
    <div
      ref={containerRef}
      className="h-64 w-full rounded-xl border border-ink-200 dark:border-ink-700"
      aria-label="Карта для выбора места работы"
    />
  );
}
