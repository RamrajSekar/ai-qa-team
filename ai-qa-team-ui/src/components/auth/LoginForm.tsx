"use client";

import { useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";

export default function LoginForm() {
  const { loginWithEmail } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function submit(e: any) {
    e.preventDefault();
    await loginWithEmail(email, password);
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <input
        type="email"
        placeholder="Email"
        required
        className="w-full px-4 py-3 rounded-lg border border-gray-300 
                   focus:ring-2 focus:ring-indigo-500 text-gray-900"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <input
        type="password"
        placeholder="Password"
        required
        className="w-full px-4 py-3 rounded-lg border border-gray-300 
                   focus:ring-2 focus:ring-indigo-500 text-gray-900"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button
        type="submit"
        className="
          w-full py-3 rounded-lg bg-indigo-600 text-white font-semibold
          hover:bg-indigo-700 transition shadow
        "
      >
        Log in
      </button>
    </form>
  );
}
