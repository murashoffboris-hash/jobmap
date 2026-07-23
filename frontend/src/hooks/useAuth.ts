import { useEffect } from "react";
import { useAuthStore } from "@/store/auth";

// Тонкая обёртка: точечно прокидывает bootstrap-эффект наружу,
// чтобы компоненты не знали про детали стора.
export function useAuthBootstrap(): void {
  const bootstrap = useAuthStore((s) => s.bootstrap);
  const status = useAuthStore((s) => s.status);

  useEffect(() => {
    if (status === "idle") {
      void bootstrap();
    }
  }, [bootstrap, status]);
}
