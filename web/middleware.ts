import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";

/**
 * Server-side auth middleware to prevent flash of protected content.
 * Redirects unauthenticated users from /app/* to /login before any JS
 * is sent (Issue #12).
 *
 * Uses @supabase/ssr createServerClient to read the auth session from
 * cookies. If no valid session exists, redirects to /login with the
 * original destination as a redirect param.
 */
export async function middleware(request: NextRequest) {
  // Only protect /app routes
  if (!request.nextUrl.pathname.startsWith("/app")) {
    return NextResponse.next();
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  // If Supabase is not configured, let the client-side auth handle it
  // (avoids breaking local dev without env vars).
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.next();
  }

  let response = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value, options }) => {
          response.cookies.set(name, value, options);
        });
      },
    },
  });

  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", request.nextUrl.pathname);
      return NextResponse.redirect(loginUrl, 307);
    }
  } catch {
    // On error, let the client-side auth provider handle it
  }

  return response;
}

export const config = {
  matcher: ["/app/:path*"],
};
