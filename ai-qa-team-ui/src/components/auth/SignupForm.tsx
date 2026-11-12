"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";

function signupError(status: number, detail?: unknown) {
  const message = typeof detail === "string" ? detail.toLowerCase() : "";
  if (status === 400 || message.includes("already exists")) {
    return "An account with this email already exists.";
  }
  if (status === 403 || status === 409) return "Check your invitation link, or sign in if you already have an account.";
  if (status === 422) {
    return "Please check your name, email, and password.";
  }
  return "We couldn’t create your account. Please try again.";
}

export default function SignupForm() {
  const router = useRouter();
  const { signupWithEmail } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await signupWithEmail(name.trim(), email.trim(), password);
      if (!response.ok) {
        setError(signupError(response.status, response.data?.detail));
        return;
      }
      router.push("/dashboard");
    } catch {
      setError("We couldn’t create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="auth-form">
      {error && (
        <p className="auth-error" role="alert">
          {error}
        </p>
      )}

      <label htmlFor="signup-name">Full name</label>
      <input
        id="signup-name"
        name="name"
        type="text"
        autoComplete="name"
        placeholder="Your name"
        value={name}
        onChange={(event) => setName(event.target.value)}
        required
      />

      <label htmlFor="signup-email">Work email</label>
      <input
        id="signup-email"
        name="email"
        type="email"
        autoComplete="email"
        placeholder="you@company.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        required
      />

      <label htmlFor="signup-password">Password</label>
      <input
        id="signup-password"
        name="password"
        type="password"
        autoComplete="new-password"
        placeholder="At least 8 characters"
        minLength={8}
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        required
      />

      <button type="submit" className="auth-submit" disabled={loading}>
        {loading ? "Creating account…" : "Create account"}
      </button>
    </form>
  );
}
