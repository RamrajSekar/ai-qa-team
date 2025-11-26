"use client";

import { useAuth } from "../providers/AuthProvider";
import { useState } from "react";
import { motion } from "framer-motion";

export default function AuthModal() {
  const {
    authOpen,
    closeAuth,
    mode,
    switchMode,
    loginWithEmail,
    signupWithEmail,
    loginWithGoogle,
  } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");

  if (!authOpen) return null;

  async function onSubmit(e: any) {
    e.preventDefault();
    if (mode === "login") {
      await loginWithEmail(email, password);
    } else {
      await signupWithEmail(email, password, name);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6"
      >
        {/* Tabs */}
        <div className="flex justify-center mb-6">
          <button
            className={`px-6 py-2 text-sm font-semibold rounded-full ${
              mode === "login" ? "bg-indigo-600 text-white" : "text-gray-600"
            }`}
            onClick={() => switchMode("login")}
          >
            Login
          </button>

          <button
            className={`px-6 py-2 text-sm font-semibold rounded-full ml-2 ${
              mode === "signup" ? "bg-indigo-600 text-white" : "text-gray-600"
            }`}
            onClick={() => switchMode("signup")}
          >
            Signup
          </button>
        </div>

        {/* Form */}
        <form onSubmit={onSubmit} className="space-y-4">
          {mode === "signup" && (
            <input
              className="w-full border p-3 rounded-xl"
              placeholder="Full Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          )}

          <input
            className="w-full border p-3 rounded-xl"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <input
            className="w-full border p-3 rounded-xl"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button
            type="submit"
            className="w-full bg-indigo-600 text-white py-3 rounded-xl mt-2 font-semibold"
          >
            {mode === "login" ? "Login" : "Create Account"}
          </button>
        </form>

        {/* OAuth */}
        <button
          onClick={loginWithGoogle}
          className="w-full mt-4 border py-3 rounded-xl flex items-center justify-center gap-2"
        >
          <img src="/google.svg" className="h-5 w-5" />
          Continue with Google
        </button>

        {/* Close */}
        <button
          className="mt-4 text-sm text-gray-500 w-full text-center"
          onClick={closeAuth}
        >
          Close
        </button>
      </motion.div>
    </div>
  );
}
