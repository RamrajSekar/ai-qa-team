"use client";

import { useState } from "react";
import { useAuth } from "@/components/providers/AuthProvider";
import { apiFetch } from "@/utils/api";
import { useRouter } from "next/navigation";

export default function LoginForm() {
  const router = useRouter();
  const { closeAuth, setUser } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await apiFetch(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/login`,
        {
          method: "POST",
          body: JSON.stringify({ email, password }),
        }
      );

      if (!res.ok) {
        setError("Invalid login credentials");
        setLoading(false);
        return;
      }

      const data = await res.json();

      // 1️⃣ Save user to global store
      setUser(data.user);

      // 2️⃣ Close the modal
      closeAuth();

      // 3️⃣ Force hydration through /auth/me
      await apiFetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/me`);

      // 4️⃣ Redirect to dashboard
      router.push("/dashboard");
    } catch (err) {
      setError("Something went wrong");
    }

    setLoading(false);
  }

  return (
    <form onSubmit={handleLogin} className="space-y-4">
      {error && (
        <p className="text-red-600 text-sm text-center">{error}</p>
      )}

      <input
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
        placeholder="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <input
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
        placeholder="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-indigo-600 text-white py-3 rounded-lg hover:bg-indigo-700 transition"
      >
        {loading ? "Logging in..." : "Log in"}
      </button>
    </form>
  );
}
