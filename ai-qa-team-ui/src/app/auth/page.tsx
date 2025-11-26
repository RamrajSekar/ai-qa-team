"use client";

import { Suspense } from "react";
import AuthEntryPageInner from "./pageInner";

export default function AuthEntryPage() {
  return (
    <Suspense fallback={null}>
      <AuthEntryPageInner />
    </Suspense>
  );
}
