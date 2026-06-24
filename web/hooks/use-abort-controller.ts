"use client";

import { useEffect, useRef, useCallback } from "react";

/**
 * Hook that creates an AbortController tied to the component lifecycle.
 * Automatically aborts on unmount. Pass the signal to fetch/apiRequest calls
 * to cancel pending requests when the user navigates away (Issue #70, #30).
 *
 * Usage:
 *   const { signal, reset } = useAbortController();
 *   useEffect(() => {
 *     fetch("/api/data", { signal }).then(...).catch(err => {
 *       if (err.name !== "AbortError") { ... }
 *     });
 *   }, [signal]);
 */
export function useAbortController() {
  const controllerRef = useRef<AbortController | null>(null);

  // Create a new controller on mount, abort on unmount
  useEffect(() => {
    controllerRef.current = new AbortController();
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  const getSignal = useCallback((): AbortSignal | undefined => {
    return controllerRef.current?.signal;
  }, []);

  // Reset: abort the current controller and create a new one (for re-fetching)
  const reset = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = new AbortController();
    return controllerRef.current?.signal;
  }, []);

  return { getSignal, reset };
}
