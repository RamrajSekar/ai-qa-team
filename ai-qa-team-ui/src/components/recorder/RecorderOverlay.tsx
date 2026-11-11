"use client";

import { useEffect, useRef, useState } from "react";
import { X, Save } from "lucide-react";

interface RecorderOverlayProps {
  url: string;         // AUT URL
  storyId: string;
  projectId: string;
  onClose: () => void;
}

export default function RecordingOverlay({
  url,
  storyId,
  projectId,
  onClose,
}: RecorderOverlayProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [steps, setSteps] = useState<any[]>([]);

  // -------------------------------
  // Inject script + register listeners
  // -------------------------------
  const handleIframeLoad = () => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const win = iframe.contentWindow;
    const doc = win?.document;
    if (!win || !doc) return;

    console.log("[Recorder] Iframe Loaded ✓");

    // Inject recorder.js
    const script = doc.createElement("script");
    script.src = "/recorder.js"; // must be inside public/
    script.onload = () => console.log("[Recorder] recorder.js injected ✓");
    doc.head.appendChild(script);

    // CLICK events
    doc.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      const selector = getSelector(target);

      setSteps((prev) => [
        ...prev,
        {
          order: prev.length + 1,
          action: "click",
          selector,
          url: win.location.href,
          meta: {},
        },
      ]);
    });

    // INPUT events
    doc.addEventListener("input", (e) => {
      const target = e.target as HTMLInputElement;
      const selector = getSelector(target);

      setSteps((prev) => [
        ...prev,
        {
          order: prev.length + 1,
          action: "input",
          selector,
          input_value: target.value,
          url: win.location.href,
          meta: {},
        },
      ]);
    });

    // NAVIGATION events (from recorder.js)
    win.addEventListener("message", (event) => {
      if (event.data?.type === "recorder:navigation") {
        setSteps((prev) => [
          ...prev,
          {
            order: prev.length + 1,
            action: "navigate",
            selector: null,
            url: event.data.url,
            meta: {},
          },
        ]);
      }
    });
  };

  // -------------------------------
  // Generate CSS selector
  // -------------------------------
  const getSelector = (el: HTMLElement | null): string => {
    if (!el) return "unknown";
    if (el.id) return `#${el.id}`;
    if (el.className) {
      const classes = el.className.toString().trim().replace(/\s+/g, ".");
      return `${el.tagName.toLowerCase()}.${classes}`;
    }
    return el.tagName.toLowerCase();
  };

  // -------------------------------
  // Save recording to backend
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
      alert("Recording saved ✔");
      onClose();
    } else {
      const err = await res.json().catch(() => ({}));
      alert(`Failed: ${err?.detail || "Unknown error"}`);
    }
  }

  // -------------------------------
  // UI
  // -------------------------------
  return (
    <div className="fixed inset-0 z-[9999] bg-black/70 flex flex-col">
      {/* HEADER */}
      <div className="bg-gray-900 text-white p-3 flex justify-between items-center">
        <div>
          <h2 className="font-semibold">Recording Mode</h2>
          <p className="text-xs opacity-60">Every interaction is captured</p>
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={saveRecording}
            className="flex items-center gap-2 bg-green-600 px-3 py-1 rounded hover:bg-green-700"
          >
            <Save size={16} /> Save
          </button>

          <button
            onClick={onClose}
            className="text-white hover:text-red-400"
          >
            <X size={26} />
          </button>
        </div>
      </div>

      {/* IFRAME */}
      <iframe
        ref={iframeRef}
        src={url}
        className="flex-1 bg-white"
        onLoad={handleIframeLoad}
      />
    </div>
  );
}
