"use client";

import { useEffect } from "react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log full error details to console only — never show raw message to user
    // (Issue: PR review — avoid information disclosure).
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="text-center max-w-md">
        <h2 className="text-2xl font-bold">Something went wrong</h2>
        <p className="mt-2 text-sm text-muted-foreground" role="alert">
          An unexpected error occurred. Try again, or contact support if the problem persists.
        </p>
        <div className="mt-6 flex gap-3 justify-center">
          <button type="button" onClick={reset} className={buttonVariants({ variant: "default" })}>
            Try again
          </button>
          <Link href="/" className={buttonVariants({ variant: "outline" })}>
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
