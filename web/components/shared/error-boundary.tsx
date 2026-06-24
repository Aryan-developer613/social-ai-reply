"use client";

import { Component, type ReactNode, type ErrorInfo } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

type Props = { children: ReactNode };
type State = { hasError: boolean; message: string };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: "" };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to error reporting service (e.g., Sentry, LogRocket)
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      const isConfigError = this.state.message.includes("Supabase environment variables");
      const displayMessage = isConfigError
        ? "Authentication is not configured. Please check your environment variables and reload."
        : this.state.message || "An unexpected error occurred.";

      return (
        <div className="flex min-h-[200px] flex-col items-center justify-center rounded-xl border border-destructive/20 bg-destructive/5 p-8 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/10">
            <AlertTriangle className="h-7 w-7 text-destructive" />
          </div>
          <p className="mt-4 text-base font-semibold text-foreground">Something went wrong</p>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">{displayMessage}</p>
          {isConfigError ? (
            <Button variant="outline" size="sm" className="mt-4" onClick={() => window.location.reload()}>
              Reload
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => this.setState({ hasError: false, message: "" })}
            >
              Try again
            </Button>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
