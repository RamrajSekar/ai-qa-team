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
   UNIFIED apiFetch — every API call returns:
   { ok, status, data }
----------------------------------------------------- */
export async function apiFetch(url: string, options: APIOptions = {}): Promise<ApiResponse> {
  const path = url.startsWith("http")
    ? url
    : `${API_URL}${url}`;

  const opts: RequestInit = {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  };

  let res = await fetch(path, opts);

  // Token expired → attempt refresh
  if (res.status === 401 && !options.retry) {
    console.log("🔄 Access token expired → Attempting refresh...");

    const refresh = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });

    if (refresh.ok) {
      console.log("🔐 Refresh OK → retrying original request...");
      return apiFetch(path, { ...options, retry: true });
    }

    console.log("❌ Refresh failed — returning original response.");
  }

  // Always return unified data structure
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }

  return {
    ok: res.ok,
    status: res.status,
    data,
  };
}