import { apiClient } from "./client";
import type { GeocodeResult } from "@/types";

export const geoApi = {
  /** Geocode address → coordinates via backend nominatim proxy */
  async geocode(address: string): Promise<GeocodeResult[]> {
    const res = await apiClient.post<GeocodeResult>("/geo/geocode", {
      address,
    });
    // Backend returns a single result; wrap in array for autocomplete dropdown
    return [res.data];
  },

  /** Reverse geocode coordinates → address */
  async reverse(lat: number, lng: number): Promise<GeocodeResult> {
    const res = await apiClient.get<GeocodeResult>("/geo/reverse", {
      params: { lat, lon: lng },
    });
    return res.data;
  },
};
