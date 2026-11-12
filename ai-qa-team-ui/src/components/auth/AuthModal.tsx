"use client";

import { Check, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/AuthProvider";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import LoginForm from "./LoginForm";
import SignupForm from "./SignupForm";
import OAuthButton from "./OAuthButton";
import "./auth.css";

export default function AuthModal() {
  const pathname = usePathname();
  const router = useRouter();
  const { authOpen, closeAuth, mode, switchMode } = useAuth();
  const isLogin = mode === "login";

  function handleOpenChange(open: boolean) {
    if (open) return;
    closeAuth();
    if (pathname === "/auth") router.replace("/");
  }

  return (
    <Dialog open={authOpen} onOpenChange={handleOpenChange}>
      <DialogContent className="auth-modal" showCloseButton={false}>
        <DialogClose className="auth-close" aria-label="Close authentication dialog">
          <X size={18} aria-hidden="true" />
        </DialogClose>

        <aside className="auth-aside">
          <div className="auth-brand">
            <span>QA</span>
            AI QA Team
          </div>
          <div>
            <p className="auth-eyebrow">Product knowledge. Reviewed tests.</p>
            <h2>Give your QA team shared product understanding.</h2>
            <p>
              Review product knowledge, clarify stories and create test designs with explicit
              expected results.
            </p>
          </div>
          <ul className="auth-benefits">
            {[
              "Approved product knowledge",
              "Story-based scenarios and test cases",
              "Human review stays in control",
            ].map((benefit) => (
              <li key={benefit}>
                <Check size={15} aria-hidden="true" />
                {benefit}
              </li>
            ))}
          </ul>
        </aside>

        <div className="auth-pane">
          <div className="auth-heading">
            <DialogTitle>{isLogin ? "Welcome back" : "Create your account"}</DialogTitle>
            <DialogDescription>
              {isLogin
                ? "Sign in to continue to your AI QA Team workspace."
                : "Set up your workspace using email or Google."}
            </DialogDescription>
          </div>

          <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
            <button
              type="button"
              role="tab"
              aria-selected={isLogin}
              className={isLogin ? "is-active" : ""}
              onClick={() => switchMode("login")}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={!isLogin}
              className={!isLogin ? "is-active" : ""}
              onClick={() => switchMode("signup")}
            >
              Sign up
            </button>
          </div>

          <div role="tabpanel" aria-label={isLogin ? "Sign in" : "Sign up"}>
            {isLogin ? <LoginForm /> : <SignupForm />}
          </div>

          <div className="auth-divider" aria-hidden="true">
            <span>or</span>
          </div>
          <OAuthButton />

          <p className="auth-switch">
            {isLogin ? "New to AI QA Team?" : "Already have an account?"}{" "}
            <button type="button" onClick={() => switchMode(isLogin ? "signup" : "login")}>
              {isLogin ? "Create an account" : "Sign in"}
            </button>
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
