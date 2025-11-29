import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Protected routes
const PROTECTED = [
  "/dashboard",
  "/projects",
  "/scenarios",
  "/executions",
  "/settings",
  "/ai",
];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Determine if the path is protected
  const isProtected = PROTECTED.some((route) =>
    pathname.startsWith(route)
  );

  if (!isProtected) {
    return NextResponse.next();
  }

  // Check cookie
  // const accessToken = req.cookies.get("access_token")?.value;

  // if (!accessToken) {
  //   // Redirect to homepage or login page
  //   const loginUrl = new URL("/", req.url);
  //   loginUrl.searchParams.set("auth", "login-required");
  //   return NextResponse.redirect(loginUrl);
  // }
  if (isProtected) {
  const accessToken = req.cookies.get("access_token")?.value;
  if (!accessToken) {
     const loginUrl = new URL("/", req.url);
     loginUrl.searchParams.set("auth", "login-required");
     return NextResponse.redirect(loginUrl);
    }
  }


  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/projects/:path*",
    "/scenarios/:path*",
    "/executions/:path*",
    "/settings/:path*",
    "/ai/:path*",
  ],
};
