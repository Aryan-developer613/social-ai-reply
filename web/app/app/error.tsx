"use client";

import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";

export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-4">
      <div className="text-center max-w-md">
        <h2 className="text-xl font-semibold">Page Error</h2>
        <p className="mt-2 text-sm text-muted-foreground" role="alert">
          This page encountered an error. Try again, or navigate elsewhere.
        </p>
        <div className="mt-6 flex gap-3 justify-center">
          <button type="button" onClick={reset} className={buttonVariants({ variant: "default" })}>
            Retry
          </button>
          <Link href="/" className={buttonVariants({ variant: "outline" })}>
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
