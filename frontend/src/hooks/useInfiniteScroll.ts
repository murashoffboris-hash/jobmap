import { useRef, useEffect, useCallback } from "react";

export interface UseInfiniteScrollOptions {
  /** Called when the sentinel enters the viewport and loading is not already in progress. */
  onLoadMore: () => void;
  /** Whether a fetch is currently in flight — prevents duplicate fires. */
  loading: boolean;
  /** Stop observing when there is no more data to load. */
  hasMore: boolean;
  /** RootMargin for IntersectionObserver (default "200px" triggers a bit before reaching end). */
  rootMargin?: string;
}

/**
 * Custom hook that attaches an IntersectionObserver to a sentinel element.
 * Fires `onLoadMore` when the sentinel scrolls into view, the observer is
 * active (hasMore === true), and no load is currently in progress.
 *
 * Returns a ref callback to attach to the sentinel element, plus a `reset`
 * function to force-reconnect the observer (useful after filters change).
 */
export function useInfiniteScroll({
  onLoadMore,
  loading,
  hasMore,
  rootMargin = "200px",
}: UseInfiniteScrollOptions) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<IntersectionObserver | null>(null);
  // Keep callbacks in refs so the observer always sees the latest values
  const onLoadMoreRef = useRef(onLoadMore);
  const loadingRef = useRef(loading);
  const hasMoreRef = useRef(hasMore);

  onLoadMoreRef.current = onLoadMore;
  loadingRef.current = loading;
  hasMoreRef.current = hasMore;

  const disconnect = useCallback(() => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    disconnect();
    const el = sentinelRef.current;
    if (!el || !hasMoreRef.current) return;

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasMoreRef.current && !loadingRef.current) {
          onLoadMoreRef.current();
        }
      },
      { rootMargin },
    );
    observerRef.current.observe(el);
  }, [disconnect, rootMargin]);

  // Attach observer when hasMore changes or component mounts
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect, hasMore]);

  const sentinelCallback = useCallback(
    (node: HTMLDivElement | null) => {
      sentinelRef.current = node;
      connect();
    },
    [connect],
  );

  return { sentinelRef: sentinelCallback, reset: connect };
}
