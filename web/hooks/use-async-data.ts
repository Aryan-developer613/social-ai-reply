"use client";

/**
 * Shared "load once (or on dep change), track loading/error" hook for the
 * common `useState(loading) + useState(data) + useEffect(load)` pattern
 * repeated across page components. Use `reload(true)` for a silent
 * background refresh that doesn't flip `loading` back to true.
 */

import { useCallback, useEffect, useRef, useState, type DependencyList } from "react";
import { getErrorMessage } from "@/types/errors";

interface UseAsyncDataOptions {
  /** Skip fetching entirely (e.g. while a required token/id isn't ready yet). */
  enabled?: boolean;
  onError?: (message: string) => void;
}

export interface UseAsyncDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  /** Re-run the fetcher. Pass `true` to refresh without flipping `loading`. */
  reload: (silent?: boolean) => Promise<void>;
  setData: React.Dispatch<React.SetStateAction<T | null>>;
}

export function useAsyncData<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList,
  options: UseAsyncDataOptions = {},
): UseAsyncDataResult<T> {
  const { enabled = true, onError } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  // Ref so `reload`'s identity stays stable across renders while always
  // calling the latest fetcher (avoids re-triggering the load effect below
  // just because the caller passed a fresh inline function).
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  // Monotonic request id — guards against an older in-flight call (e.g. for
  // a since-changed selected project) resolving after a newer one and
  // clobbering state with stale data (same pattern as content/page.tsx's
  // loadDraftsRequestRef).
  const requestIdRef = useRef(0);

  const reload = useCallback(
    async (silent = false) => {
      if (!enabled) return;
      const requestId = ++requestIdRef.current;
      if (!silent) setLoading(true);
      try {
        const result = await fetcherRef.current();
        if (requestIdRef.current !== requestId) return;
        setData(result);
        // Only clear a previous error once we know the outcome — clearing
        // it up front would flash an error banner blank during a silent
        // background refresh even before the retry has actually succeeded.
        setError(null);
        if (!silent) setLoading(false);
      } catch (err) {
        if (requestIdRef.current !== requestId) return;
        const message = getErrorMessage(err);
        setError(message);
        onError?.(message);
        if (!silent) setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [enabled, onError],
  );

  useEffect(() => {
    void reload(false);
    // `deps` is caller-supplied and intentionally spread — this hook exists
    // precisely so callers don't re-declare the load-on-mount effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps]);

  return { data, loading, error, reload, setData };
}
