"use client";

import { useRouter } from "next/navigation";

export interface StepFooterProps {
  next?: string;        // URL to navigate forward
  back?: string;        // URL to navigate backward
  disableNext?: boolean;
}

export default function StepFooter({
  next,
  back,
  disableNext = false,
}: StepFooterProps) {
  const router = useRouter();

  return (
    <div className="mt-10 flex justify-between w-full">
      {/* BACK BUTTON */}
      <button
        className="px-4 py-2 rounded-md border"
        disabled={!back}
        onClick={() => back && router.push(back)}
      >
        Back
      </button>

      {/* NEXT BUTTON */}
      <button
        className="px-4 py-2 rounded-md bg-purple-600 text-white disabled:bg-gray-300"
        disabled={disableNext || !next}
        onClick={() => next && !disableNext && router.push(next)}
      >
        Continue
      </button>
    </div>
  );
}

// ✔ default export
// export default StepFooter;

// ✔ named export (fixes your error)
// export const StepFooter = StepFooterComponent;1