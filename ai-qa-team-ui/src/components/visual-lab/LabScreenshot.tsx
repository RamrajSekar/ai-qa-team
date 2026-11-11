"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

export default function LabScreenshot({ url, label }: { url: string; label: string }) {
  const [source, setSource] = useState<string>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | undefined;
    fetch(`${process.env.NEXT_PUBLIC_API_URL}${url}`, { credentials: "include", cache: "no-store", signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("Screenshot unavailable");
        const blob = await response.blob();
        if (!controller.signal.aborted) { objectUrl = URL.createObjectURL(blob); setSource(objectUrl); }
      }).catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url]);
  return <figure className="rounded-xl border p-3"><figcaption className="mb-2 text-sm">{label}</figcaption>
    {source ? <Image unoptimized src={source} alt={`Controlled sample: ${label}`} width={1000} height={800} className="w-full h-auto rounded-lg" />
      : <p role="status">{failed ? "Screenshot unavailable. Refresh or sign in again." : "Loading screenshot…"}</p>}</figure>;
}
