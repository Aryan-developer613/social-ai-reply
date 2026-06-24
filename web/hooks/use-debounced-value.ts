"use client";

import { useEffect, useState } from "react";

/**
 * Debounce a rapidly-changing value (e.g. a search input).
 * Returns the debounced value after the specified delay (Issue #71, #35).
 *
 * Usage:
 *   const [search, setSearch] = useState("");
 *   const debouncedSearch = useDebouncedValue(search, 200);
 *   useEffect(() => {
 *     if (debouncedSearch) { fetchResults(debouncedSearch); }
 *   }, [debouncedSearch]);
 */
export function useDebouncedValue<T>(value: T, delayMs = 200): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
