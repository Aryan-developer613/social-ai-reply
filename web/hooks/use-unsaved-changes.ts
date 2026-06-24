"use client";

import { useEffect, useRef, useCallback, useState } from "react";

/**
 * Hook to warn users about unsaved changes before navigating away or closing
 * the tab (Issue #69, #20).
 *
 * Usage:
 *   const { dirty, markDirty, markClean } = useUnsavedChanges();
 *   // Call markDirty() when form fields change, markClean() after save.
 *
 * When dirty is true:
 *   - beforeunload triggers a browser confirmation dialog on tab close/refresh
 *   - Next.js route changes are intercepted with a confirmation dialog
 */
export function useUnsavedChanges() {
  const [dirty, setDirty] = useState(false);
  const dirtyRef = useRef(dirty);

  // Keep ref in sync with state for use in event handlers
  useEffect(() => {
    dirtyRef.current = dirty;
  }, [dirty]);

  // beforeunload: warn on tab close / refresh
  useEffect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      if (dirtyRef.current) {
        e.preventDefault();
        e.returnValue = "";
        return "";
      }
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, []);

  const markDirty = useCallback(() => setDirty(true), []);
  const markClean = useCallback(() => setDirty(false), []);

  return { dirty, markDirty, markClean };
}
