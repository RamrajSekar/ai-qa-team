"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { useAuth } from "@/components/providers/AuthProvider";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";
import OAuthButton from "./OAuthButton";

export default function AuthModal() {
  const { authOpen, closeAuth, mode, switchMode } = useAuth();

  return (
    <AnimatePresence>
      {authOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-md bg-white text-gray-900 rounded-2xl p-8 shadow-2xl border border-gray-200 relative overflow-hidden"
          >
            {/* Close */}
            <button
              onClick={closeAuth}
              className="absolute right-4 top-4 text-gray-500 hover:text-gray-700"
            >
              <X size={22} />
            </button>

            {/* Tabs */}
            <div className="flex justify-center mb-6 gap-3">
              <button
                onClick={() => switchMode("login")}
                className={`
                  px-5 py-2 rounded-full text-sm font-medium transition 
                  ${
                    mode === "login"
                      ? "bg-indigo-600 text-white shadow"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }
                `}
              >
                Login
              </button>

              <button
                onClick={() => switchMode("signup")}
                className={`
                  px-5 py-2 rounded-full text-sm font-medium transition 
                  ${
                    mode === "signup"
                      ? "bg-indigo-600 text-white shadow"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }
                `}
              >
                Sign up
              </button>
            </div>

            {/* Forms */}
            <AnimatePresence mode="wait">
              {mode === "login" ? (
                <motion.div
                  key="login"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                >
                  <LoginForm />
                </motion.div>
              ) : (
                <motion.div
                  key="signup"
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                >
                  <SignupForm />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Divider */}
            <div className="flex items-center my-6">
              <div className="flex-1 h-px bg-gray-300" />
              <span className="px-4 text-gray-500 text-sm">OR</span>
              <div className="flex-1 h-px bg-gray-300" />
            </div>

            {/* OAuth */}
            <OAuthButton />
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
