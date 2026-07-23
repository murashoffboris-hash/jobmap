import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "by.service247.jobmap",
  appName: "JobMap",
  webDir: "dist",
  bundledWebRuntime: false,
  server: {
    // В проде nginx раздаёт build; здесь можно указать API endpoint.
    androidScheme: "https",
    iosScheme: "https",
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 1500,
      backgroundColor: "#0f172a",
      androidScaleType: "CENTER_CROP",
      showSpinner: true,
      spinnerColor: "#ffffff",
    },
    StatusBar: {
      style: "DARK",
      backgroundColor: "#0f172a",
    },
  },
};

export default config;
