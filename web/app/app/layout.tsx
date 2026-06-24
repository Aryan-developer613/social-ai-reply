import AppShell from "@/components/app/app-shell";

// ErrorBoundary wrapping removed — the per-route app/error.tsx now handles
// render errors for the authenticated area (Issue #52). The previous double
// wrapping (AppShell > ErrorBoundary > children) caused inline error UI
// instead of a full-page branded error.
export default function AuthenticatedLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
