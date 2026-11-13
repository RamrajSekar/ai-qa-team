const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

interface APIOptions extends RequestInit {
  retry?: boolean;
}

interface ApiResponse {
  ok: boolean;
  status: number;
  // Existing callers consume heterogeneous legacy API payloads.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
}

// One refresh per API origin while a page's parallel reads restore a session.
// This is coordination only: no response or account data is cached.
const refreshes = new Map<string, Promise<boolean>>();
function refreshSession(base: string): Promise<boolean> {
  let pending = refreshes.get(base);
  if (!pending) {
    pending = fetch(`${base}/auth/refresh`, {
      method: "POST", credentials: "include", signal: AbortSignal.timeout(10000),
    }).then(response => response.ok).catch(() => false).finally(() => refreshes.delete(base));
    refreshes.set(base, pending);
  }
  return pending;
}

function waitForRefresh(pending: Promise<boolean>, signal?: AbortSignal | null): Promise<boolean> {
  if (!signal) return pending;
  signal.throwIfAborted();
  return new Promise((resolve, reject) => {
    const abort = () => reject(signal.reason);
    signal.addEventListener("abort", abort, { once: true });
    pending.then(resolve, reject).finally(() => signal.removeEventListener("abort", abort));
  });
}

/* -----------------------------------------------------
   UNIFIED & ROBUST apiFetch() — NEVER breaks UI
   Handles:
   ✔ Raw lists (FastAPI returns list)
   ✔ JSON objects
   ✔ { data: ... } formats
   ✔ Empty responses
   ✔ Token refresh flow
----------------------------------------------------- */
export async function apiFetch(url: string, options: APIOptions = {}): Promise<ApiResponse> {
  const path = url.startsWith("http") ? url : `${API_URL}${url}`;

  const { retry, ...requestOptions } = options;
  const headers = new Headers(options.headers);
  // A JSON header on bodyless GETs adds cross-origin preflights. Preserve
  // explicit caller headers and let the browser supply multipart boundaries.
  if (typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const opts: RequestInit = { credentials: "include", ...requestOptions, headers };

  const res = await fetch(path, opts);

  /* ----------------------------
     AUTO REFRESH TOKEN FLOW
  ---------------------------- */
  const authAction = /\/auth\/(login|signup|refresh|logout)(?:[?#]|$)/.test(path);
  if (res.status === 401 && !retry && !authAction) {
    options.signal?.throwIfAborted();
    const refreshed = await waitForRefresh(refreshSession(API_URL), options.signal);
    options.signal?.throwIfAborted();
    if (refreshed) {
      return apiFetch(path, { ...options, retry: true });
    }
  }

  /* ----------------------------
     SAFE JSON PARSING
  ---------------------------- */
  let raw: unknown = null;
  try {
    raw = await res.json();
  } catch {
    raw = null;
  }

  /* ----------------------------
     UNIFIED DATA NORMALIZATION
  ---------------------------- */

  // Case 1: FastAPI returns raw list → keep as data
  if (Array.isArray(raw)) {
    return {
      ok: res.ok,
      status: res.status,
      data: raw,
    };
  }

  // Case 2: FastAPI returns an object with data wrapper
  if (raw && typeof raw === "object" && "data" in raw) {
    return {
      ok: res.ok,
      status: res.status,
      data: raw.data,
    };
  }

  // Case 3: regular object or null
  return {
    ok: res.ok,
    status: res.status,
    data: raw,
  };
}
