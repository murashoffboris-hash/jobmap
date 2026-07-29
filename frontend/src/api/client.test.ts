import { describe, expect, it, vi, beforeEach } from "vitest";

// Только тесты storage-функций — БЕЗ моков axios
const store = new Map<string, string>();
const localStorageMock = {
  getItem: vi.fn((key: string) => store.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => { store.set(key, value); }),
  removeItem: vi.fn((key: string) => { store.delete(key); }),
  clear: vi.fn(() => { store.clear(); }),
  get length() { return store.size; },
  key: vi.fn((_index: number) => null),
};
Object.defineProperty(globalThis, "localStorage", { value: localStorageMock, writable: true });

import { getRefreshToken, setRefreshToken } from "./client";

describe("getRefreshToken / setRefreshToken", () => {
  beforeEach(() => {
    store.clear();
    vi.clearAllMocks();
  });

  it("сохраняет refresh_token в localStorage", () => {
    setRefreshToken("my-refresh-token");
    expect(store.get("jobmap.auth.refresh")).toBe("my-refresh-token");
  });

  it("читает refresh_token из localStorage", () => {
    store.set("jobmap.auth.refresh", "stored-refresh");
    expect(getRefreshToken()).toBe("stored-refresh");
  });

  it("возвращает null, если refresh_token отсутствует", () => {
    expect(getRefreshToken()).toBeNull();
  });

  it("setRefreshToken(null) удаляет ключ из localStorage", () => {
    store.set("jobmap.auth.refresh", "some-token");
    setRefreshToken(null);
    expect(store.has("jobmap.auth.refresh")).toBe(false);
  });

  it("возвращает null при ошибке localStorage (getRefreshToken)", () => {
    localStorageMock.getItem.mockImplementationOnce(() => { throw new Error("quota"); });
    expect(getRefreshToken()).toBeNull();
  });

  it("не бросает исключение при ошибке localStorage (setRefreshToken)", () => {
    localStorageMock.setItem.mockImplementationOnce(() => { throw new Error("quota"); });
    expect(() => setRefreshToken("x")).not.toThrow();
  });
});
