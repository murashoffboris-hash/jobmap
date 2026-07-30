import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useInfiniteScroll } from "./useInfiniteScroll";

describe("useInfiniteScroll", () => {
  let mockObserve: ReturnType<typeof vi.fn>;
  let mockDisconnect: ReturnType<typeof vi.fn>;
  let observerCallback: IntersectionObserverCallback | null;

  beforeEach(() => {
    mockObserve = vi.fn();
    mockDisconnect = vi.fn();
    observerCallback = null;

    vi.stubGlobal(
      "IntersectionObserver",
      vi.fn((cb: IntersectionObserverCallback) => {
        observerCallback = cb;
        return {
          observe: mockObserve,
          disconnect: mockDisconnect,
          unobserve: vi.fn(),
          takeRecords: vi.fn(() => []),
          root: null,
          rootMargin: "",
          thresholds: [],
        };
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("создаёт IntersectionObserver когда hasMore=true", () => {
    const onLoadMore = vi.fn();

    renderHook(() =>
      useInfiniteScroll({ onLoadMore, loading: false, hasMore: true }),
    );

    // Observer is created after sentinel ref is set (via callback)
    expect(IntersectionObserver).not.toHaveBeenCalled(); // need sentinel ref
  });

  it("не вызывает onLoadMore когда loading=true", () => {
    const onLoadMore = vi.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, loading: true, hasMore: true }),
    );

    // Create a fake sentinel element and attach it
    const div = document.createElement("div");
    act(() => {
      result.current.sentinelRef(div);
    });

    expect(IntersectionObserver).toHaveBeenCalled();
    expect(mockObserve).toHaveBeenCalledWith(div);

    // Trigger intersection while loading
    act(() => {
      observerCallback!(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it("вызывает onLoadMore когда sentinel появляется и не loading", () => {
    const onLoadMore = vi.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, loading: false, hasMore: true }),
    );

    const div = document.createElement("div");
    act(() => {
      result.current.sentinelRef(div);
    });

    act(() => {
      observerCallback!(
        [{ isIntersecting: true } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });

    expect(onLoadMore).toHaveBeenCalledOnce();
  });

  it("не вызывает onLoadMore когда hasMore=false", () => {
    const onLoadMore = vi.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, loading: false, hasMore: false }),
    );

    const div = document.createElement("div");
    act(() => {
      result.current.sentinelRef(div);
    });

    // Observer should not be created when hasMore=false
    expect(IntersectionObserver).not.toHaveBeenCalled();
  });

  it("не вызывает onLoadMore когда не пересекается", () => {
    const onLoadMore = vi.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, loading: false, hasMore: true }),
    );

    const div = document.createElement("div");
    act(() => {
      result.current.sentinelRef(div);
    });

    act(() => {
      observerCallback!(
        [{ isIntersecting: false } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      );
    });

    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it("отключает observer при размонтировании", () => {
    const onLoadMore = vi.fn();

    const { result, unmount } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, loading: false, hasMore: true }),
    );

    const div = document.createElement("div");
    act(() => {
      result.current.sentinelRef(div);
    });

    expect(mockObserve).toHaveBeenCalled();

    unmount();
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it("reset переподключает observer", () => {
    const onLoadMore = vi.fn();

    const { result } = renderHook(() =>
      useInfiniteScroll({ onLoadMore, loading: false, hasMore: true }),
    );

    const div = document.createElement("div");
    act(() => {
      result.current.sentinelRef(div);
    });

    expect(mockObserve).toHaveBeenCalledTimes(1);

    // Reset should disconnect and reconnect
    act(() => {
      result.current.reset();
    });

    expect(mockDisconnect).toHaveBeenCalled();
    expect(mockObserve).toHaveBeenCalledTimes(2);
  });
});
