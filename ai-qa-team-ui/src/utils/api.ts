const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

interface APIOptions extends RequestInit {
  retry?: boolean;
}

interface ApiResponse {
  ok: boolean;
  status: number;
  data: any;
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

  const opts: RequestInit = {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  };

  let res = await fetch(path, opts);

  /* ----------------------------
     AUTO REFRESH TOKEN FLOW
  ---------------------------- */
  if (res.status === 401 && !options.retry) {
    console.log("🔄 Access token expired → refreshing...");

    const refresh = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });

    if (refresh.ok) {
      console.log("🔐 Refresh success → retrying original request...");
      return apiFetch(path, { ...options, retry: true });
    }

    console.log("❌ Refresh failed, user must login.");
  }

  /* ----------------------------
     SAFE JSON PARSING
  ---------------------------- */
  let raw: any = null;
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
