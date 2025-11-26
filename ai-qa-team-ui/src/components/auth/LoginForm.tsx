"use client";

import { useState } from "react";
import { useAuth } from "../providers/AuthProvider";

export default function LoginForm() {
  const { loginWithEmail, loginWithGoogle, closeAuth } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function submit(e: any) {
    e.preventDefault();
    await loginWithEmail(email, password);
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <input
        className="w-full rounded-xl border px-3 py-2"
        placeholder="Email"
        type="email"
        required
        onChange={(e) => setEmail(e.target.value)}
      />

      <input
        className="w-full rounded-xl border px-3 py-2"
        placeholder="Password"
        type="password"
        required
        onChange={(e) => setPassword(e.target.value)}
      />

      <button className="w-full bg-violet-600 text-white py-2 rounded-xl mt-2">
        Continue
      </button>

      <button
        type="button"
        onClick={loginWithGoogle}
        className="w-full bg-gray-100 py-2 rounded-xl"
      >
        Continue with Google
      </button>
    </form>
  );
}
