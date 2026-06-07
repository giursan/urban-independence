// Auth is removed for direct testing, so there is no session to refresh here.
// Kept as a passthrough; restore the Supabase session-refresh logic when real
// auth comes back.
import { NextResponse, type NextRequest } from "next/server";

export function proxy(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|manifest.webmanifest|sw.js|icon.svg|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
