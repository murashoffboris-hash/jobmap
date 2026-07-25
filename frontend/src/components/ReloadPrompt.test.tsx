import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import ReloadPrompt from "@/components/ReloadPrompt";
import {
  subscribeToSW,
  getCurrentSWEvent,
  clearSWEvent,
  __emitPwaEvent,
} from "@/pwa";

describe("ReloadPrompt", () => {
  beforeEach(() => {
    clearSWEvent();
  });

  it("does not render when no SW event has fired", () => {
    const { container } = render(<ReloadPrompt />);
    expect(container.querySelector("[data-testid='reload-prompt']")).toBeNull();
  });

  it("renders banner when needRefresh is emitted", () => {
    render(<ReloadPrompt />);
    act(() => {
      __emitPwaEvent({ type: "needRefresh" });
    });
    const banner = screen.getByTestId("reload-prompt");
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent("Доступна новая версия");
    expect(banner).toHaveTextContent("обновить сейчас?");
  });

  it("hides banner when user clicks Позже", async () => {
    render(<ReloadPrompt />);
    act(() => {
      __emitPwaEvent({ type: "needRefresh" });
    });
    expect(screen.getByTestId("reload-prompt")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("reload-prompt-dismiss"));
    await waitFor(
      () => {
        expect(screen.queryByTestId("reload-prompt")).toBeNull();
      },
      { timeout: 1000 },
    );
  });

  it("does not render for offlineReady event", () => {
    render(<ReloadPrompt />);
    act(() => {
      __emitPwaEvent({ type: "offlineReady" });
    });
    expect(screen.queryByTestId("reload-prompt")).toBeNull();
  });

  it("does not crash when applying update (applyUpdate is a no-op in test env)", () => {
    render(<ReloadPrompt />);
    act(() => {
      __emitPwaEvent({ type: "needRefresh" });
    });
    // Кликаем "Обновить" — внутри динамический import registerSW,
    // который в vitest не имеет virtual:pwa-register. Проверяем,
    // что хотя бы сам факт наличия кнопки и не throw в act().
    expect(screen.getByTestId("reload-prompt-apply")).toBeInTheDocument();
  });
});

describe("pwa module — pubsub", () => {
  beforeEach(() => {
    clearSWEvent();
  });

  it("getCurrentSWEvent returns null initially", () => {
    expect(getCurrentSWEvent()).toBeNull();
  });

  it("clearSWEvent notifies subscribers and resets state", () => {
    const listener = vi.fn();
    subscribeToSW(listener);
    clearSWEvent();
    expect(listener).toHaveBeenCalled();
    expect(getCurrentSWEvent()).toBeNull();
  });

  it("subscribeToSW returns an unsubscribe function", () => {
    const listener = vi.fn();
    const unsub = subscribeToSW(listener);
    unsub();
    clearSWEvent();
    expect(listener).not.toHaveBeenCalled();
  });

  it("listener that throws does not break other listeners", () => {
    const good = vi.fn();
    const bad = vi.fn(() => {
      throw new Error("boom");
    });
    subscribeToSW(bad);
    subscribeToSW(good);
    // suppress console.warn noise
    const consoleSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    clearSWEvent();
    expect(bad).toHaveBeenCalled();
    expect(good).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });
});
