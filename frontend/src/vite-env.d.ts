/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />
/// <reference types="vitest" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_MAP_STYLE_URL: string;
  readonly VITE_MAP_DEFAULT_CENTER: string;
  readonly VITE_MAP_DEFAULT_ZOOM: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
