import { cookies } from "next/headers";

export default async function getUserServer() {
  try {
    // ⛔ Next.js 16: cookies() is async
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("access_token")?.value;

    if (!accessToken) return null;

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: "no-store",
    });

    if (!res.ok) return null;

    const json = await res.json();
    return json.user || null;

  } catch (err) {
    console.error("getUserServer error =>", err);
    return null;
  }
}
