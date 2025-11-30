// app/oauth/callback/page.tsx
import { Suspense } from "react";
import OAuthCallbackInner from "./pageInner";

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<div className="p-6">Signing you in…</div>}>
      <OAuthCallbackInner />
    </Suspense>
  );
}
