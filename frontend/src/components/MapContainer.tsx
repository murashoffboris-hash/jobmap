import { useEffect, useRef } from "react";
import maplibregl, {
  type Map as MapLibreMap,
  type Marker,
  type LngLatLike,
} from "maplibre-gl";
import { parseCenter, parseZoom } from "@/utils/format";
import type { MapPoint } from "@/types";

export interface MapContainerProps {
  points?: MapPoint[];
  center?: [number, number];
  zoom?: number;
  styleUrl?: string;
  onMarkerClick?: (point: MapPoint) => void;
  className?: string;
}

/**
 * Базовый контейнер карты на MapLibre.
 * - создаёт инстанс ровно один раз,
 * - ставит маркеры с popup по точкам,
 * - реагирует на изменение selection без пересоздания карты.
 */
export default function MapContainer(props: MapContainerProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<Marker[]>([]);

  const styleUrl =
    props.styleUrl ?? import.meta.env.VITE_MAP_STYLE_URL ?? "https://demotiles.maplibre.org/style.json";
  const center: LngLatLike = (props.center ?? parseCenter(import.meta.env.VITE_MAP_DEFAULT_CENTER)) as LngLatLike;
  const zoom = props.zoom ?? parseZoom(import.meta.env.VITE_MAP_DEFAULT_ZOOM);

  // init / cleanup
  useEffect(() => {
    if (!containerRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: styleUrl,
      center,
      zoom,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    mapRef.current = map;
    return () => {
      markersRef.current.forEach((m) => m.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
    // init ровно один раз
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // перерисовка маркеров при изменении точек
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
    const points = props.points ?? [];
    for (const p of points) {
      const el = document.createElement("div");
      el.style.width = "20px";
      el.style.height = "20px";
      el.style.borderRadius = "50%";
      el.style.background = "#f59e0b";
      el.style.border = "2px solid #0f172a";
      el.style.cursor = "pointer";
      el.title = p.title;
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        props.onMarkerClick?.(p);
      });
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([p.lng, p.lat])
        .setPopup(
          new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(
            `<strong>${escapeHtml(p.title)}</strong>`,
          ),
        )
        .addTo(map);
      markersRef.current.push(marker);
    }
    if (points.length > 0) {
      const bounds = new maplibregl.LngLatBounds();
      points.forEach((p) => bounds.extend([p.lng, p.lat]));
      map.fitBounds(bounds, { padding: 60, maxZoom: 14, duration: 600 });
    }
  }, [props.points, props.onMarkerClick]);

  return <div ref={containerRef} className={props.className ?? "map-container"} />;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
