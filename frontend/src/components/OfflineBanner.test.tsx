import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import OfflineBanner from "@/components/OfflineBanner";

// Хук слушает navigator.onLine и события window 'online'/'offline'.
// Управляем значением напрямую через Object.defineProperty.
const originalOnLine = Object.getOwnPropertyDescriptor(window.navigator, "onLine");

function setNavigatorOnline(value: boolean): void {
  Object.defineProperty(window.navigator, "onLine", {
    configurable: true,
    get: () => value,
  });
}

describe("OfflineBanner", () => {
  beforeEach(() => {
    setNavigatorOnline(true);
  });

  afterEach(() => {
    if (originalOnLine) {
      Object.defineProperty(window.navigator, "onLine", originalOnLine);
    }
    vi.restoreAllMocks();
  });

  it("does not render when online", () => {
    setNavigatorOnline(true);
    const { container } = render(<OfflineBanner />);
    expect(container.querySelector("[data-testid='offline-banner']")).toBeNull();
  });

  it("renders when navigator.onLine is false at mount", () => {
    setNavigatorOnline(false);
    render(<OfflineBanner />);
    const banner = screen.getByTestId("offline-banner");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("Нет соединения");
    expect(banner).toHaveTextContent("показаны сохранённые данные");
  });

  it("appears when 'offline' event fires", () => {
    setNavigatorOnline(true);
    render(<OfflineBanner />);
    expect(screen.queryByTestId("offline-banner")).toBeNull();

    fireEvent(window, new Event("offline"));
    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();
  });

  it("disappears when 'online' event fires", async () => {
    setNavigatorOnline(false);
    render(<OfflineBanner />);
    expect(screen.getByTestId("offline-banner")).toBeInTheDocument();

    fireEvent(window, new Event("online"));
    // framer-motion AnimatePresence держит DOM до завершения exit-анимации (~180мс).
    await waitFor(
      () => {
        expect(screen.queryByTestId("offline-banner")).toBeNull();
      },
      { timeout: 1000 },
    );
  });
});
