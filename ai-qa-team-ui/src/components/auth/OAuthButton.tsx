"use client";

import { useAuth } from "@/components/providers/AuthProvider";

export default function OAuthButton() {
  const { loginWithGoogle } = useAuth();

  return (
    <button
      onClick={loginWithGoogle}
      className="
        w-full flex items-center justify-center gap-3 
        py-3 rounded-lg border border-gray-300 bg-white text-gray-800
        hover:bg-gray-50 transition shadow-sm
      "
    >
      <img src="/google-icon.svg" className="w-5 h-5" />
      Continue with Google
    </button>
  );
}
