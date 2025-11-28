"use client";

import { useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";

export default function SignupForm() {
  const { signupWithEmail } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await signupWithEmail(name, email, password);
  }

  return (
    <form onSubmit={submit} className="space-y-4 w-full">
      <input
        type="text"
        className="
          w-full px-3 py-2 border rounded-md
          focus:outline-none focus:ring-2 focus:ring-indigo-500
        "
        placeholder="Full Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <input
        type="email"
        className="
          w-full px-3 py-2 border rounded-md
          focus:outline-none focus:ring-2 focus:ring-indigo-500
        "
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <input
        type="password"
        className="
          w-full px-3 py-2 border rounded-md
          focus:outline-none focus:ring-2 focus:ring-indigo-500
        "
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button
        type="submit"
        className="
          w-full bg-indigo-600 text-white py-2 rounded-md
          hover:bg-indigo-700 transition
        "
      >
        Sign up
      </button>
    </form>
  );
}
