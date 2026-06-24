"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";
import { m, AnimatePresence } from "framer-motion";

interface ThemeToggleProps {
  className?: string;
  showLabel?: boolean;
}

export function ThemeToggle({ className, showLabel = false }: ThemeToggleProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    // Render a matching-size invisible placeholder to prevent layout flicker (Issue #51).
    return <div className={cn("inline-flex items-center justify-center invisible", className)} style={{ width: showLabel ? "100%" : 32, height: 32 }} />;
  }

  const isDark = resolvedTheme === "dark";

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={cn(
        "relative inline-flex h-8 items-center justify-center overflow-hidden whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground",
        showLabel ? "w-full px-3" : "w-8",
        className
      )}
      aria-label="Toggle theme"
    >
      <div className={cn("relative flex items-center justify-center", showLabel ? "w-full" : "w-full h-full")}>
        <AnimatePresence mode="wait" initial={false}>
          <m.div
            key={isDark ? "dark" : "light"}
            initial={{ y: -20, opacity: 0, rotate: -90 }}
            animate={{ y: 0, opacity: 1, rotate: 0 }}
            exit={{ y: 20, opacity: 0, rotate: 90 }}
            transition={{ duration: 0.2 }}
            className="flex items-center"
          >
            {isDark ? (
              <Sun className="h-[1.2rem] w-[1.2rem] shrink-0" />
            ) : (
              <Moon className="h-[1.2rem] w-[1.2rem] shrink-0" />
            )}
          </m.div>
        </AnimatePresence>
        
        {showLabel && (
          <span className="ml-2 flex-1 text-left">
            {isDark ? "Light Mode" : "Dark Mode"}
          </span>
        )}
      </div>
    </button>
  );
}
