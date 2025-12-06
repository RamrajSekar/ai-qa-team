"use client";

import { useEffect, useState, useRef } from "react";
import { X, Save } from "lucide-react";

export default function RecorderOverlay({
  url,
  storyId,
  projectId,
  onClose,
}: {
  url: string;
  storyId: string;
  projectId: string;
  onClose: () => void;
}) {
  const [steps, setSteps] = useState<any[]>([]);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  // -------------------------------
  // Load recorder script + bind events
  // -------------------------------
  const handleIframeLoad = () => {
    const iframe = iframeRef.current;
    const win = iframe?.contentWindow;
    const doc = win?.document;

    if (!iframe || !win || !doc) return;

    console.log("[Recorder] Iframe loaded, injecting recorder.js");

    // 1️⃣ Inject recorder.js into iframe HEAD
    const script = doc.createElement("script");
    script.src = "/recorder.js"; // MUST exist in public/
    script.type = "text/javascript";

    script.onload = () => {
      console.log("[Recorder] recorder.js injected");
    };

    doc.head.appendChild(script);

    // 2️⃣ CLICK events
    doc.addEventListener("click", (e: any) => {
      const target = e.target as HTMLElement;
      const selector = getSelector(target);

      const step = {
        order: steps.length + 1,
        action: `Click: ${selector}`,
        selector,
        url: win.location.href,
        meta: {},
      };

      setSteps((prev) => [...prev, step]);
    });

    // 3️⃣ INPUT events
    doc.addEventListener("input", (e: any) => {
      const target = e.target as HTMLInputElement;
      const selector = getSelector(target);
      const value = target.value;

      const step = {
        order: steps.length + 1,
        action: `Input: ${selector}`,
        selector,
        input_value: value,
        url: win.location.href,
        meta: {},
      };

      setSteps((prev) => [...prev, step]);
    });

    // 4️⃣ Navigation events from recorder.js inside iframe
    win.addEventListener("message", (event) => {
      if (event.data?.type === "recorder:navigation") {
        console.log("[Recorder] Navigation recorded:", event.data);

        setSteps((prev) => [
          ...prev,
          {
            order: prev.length + 1,
            action: `Navigate: ${event.data.url}`,
            selector: null,
            input_value: null,
            url: event.data.url,
            meta: {},
          },
        ]);
      }
    });

    console.log("[Recorder] Event listeners attached");
  };

  // -------------------------------
  // Generate CSS selector (MVP)
  // -------------------------------
  function getSelector(el: HTMLElement | null): string {
    if (!el) return "unknown";

    if (el.id) return `#${el.id}`;
    if (el.className) {
      const classes = el.className.toString().trim().replace(/\s+/g, ".");
      return `${el.tagName.toLowerCase()}.${classes}`;
    }

    return el.tagName.toLowerCase();
  }

  // -------------------------------
  // Save to backend
  // -------------------------------
  async function saveRecording() {
    const payload = {
      story_id: storyId,
      project_id: projectId,
      steps,
    };

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/recorder/`,
      {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    );

    if (res.ok) {
      alert("Recording saved successfully!");
      onClose();
    } else {
      const err = await res.json().catch(() => ({}));
      alert(`Failed to save recording: ${err?.detail || "Unknown error"}`);
    }
  }

  // -------------------------------
  // UI Rendering
  // -------------------------------
  return (
    <div className="fixed inset-0 bg-black/70 z-[9999] flex flex-col">
      {/* HEADER */}
      <div className="bg-gray-900 text-white p-3 flex justify-between items-center">
        <div>
          <h2 className="font-semibold">Recording Mode</h2>
          <p className="text-xs opacity-80">Every interaction is being captured.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            className="flex items-center gap-1 bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm"
            onClick={saveRecording}
          >
            <Save size={16} />
            Save Recording
          </button>

          <button className="text-white hover:text-red-400" onClick={onClose}>
            <X size={28} />
          </button>
        </div>
      </div>

      {/* IFRAME */}
      <iframe
        ref={iframeRef}
        id="recorder-iframe"
        src={url}
        className="flex-1 bg-white"
        onLoad={handleIframeLoad}
      />
    </div>
  );
}
