export async function apiFetch(url: string, options: RequestInit = {}) {
  const opts: RequestInit = {
    credentials: "include", // SEND COOKIES
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  };

  let res = await fetch(url, opts);

  // If access token expired, try refresh
  if (res.status === 401) {
    const refresh = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
      {
        method: "POST",
        credentials: "include",
      }
    );

    if (refresh.ok) {
      // retry original request
      res = await fetch(url, opts);
    }
  }

  return res;
}
