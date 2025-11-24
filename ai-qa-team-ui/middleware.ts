import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Protected routes that require authentication
const PROTECTED_PATHS = [
  '/dashboard',
  '/projects',
  '/scenarios',
  '/testcases',
  '/executions',
  '/settings',
];

// Routes that should NOT be accessible when logged-in
const AUTH_PAGES = ['/login', '/signup'];

export function middleware(req: NextRequest) {
  const url = req.nextUrl.clone();
  const path = url.pathname;

  // Read tokens from cookies (set httpOnly on backend)
  const accessToken = req.cookies.get('access_token')?.value;

  const isProtected = PROTECTED_PATHS.some((route) => path.startsWith(route));
  const isAuthPage = AUTH_PAGES.includes(path);
  // 1️⃣ PROTECT PRIVATE ROUTES
  if (isProtected && !accessToken) {
    url.pathname = '/';
    url.searchParams.set('auth', 'login'); // triggers login modal
    return NextResponse.redirect(url);
  }

  // 2️⃣ REDIRECT LOGGED-IN USERS AWAY FROM LOGIN/SIGNUP
  if (isAuthPage && accessToken) {
    url.pathname = '/dashboard';
    return NextResponse.redirect(url);
  }
  console.log("MIDDLEWARE RUN:");
  console.log("Path:", req.nextUrl.pathname);
  console.log("Cookies:", req.cookies.getAll());

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/projects/:path*',
    '/scenarios/:path*',
    '/testcases/:path*',
    '/executions/:path*',
    '/settings/:path*',
    '/login',
    '/signup',
  ],
};
