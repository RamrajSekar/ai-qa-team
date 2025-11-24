"use client";

import { useState } from "react";
import AuthModal from "./AuthModal";
import { Button } from "@/components/ui/button";

export default function AuthTrigger({ children }: { children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button variant="ghost" onClick={() => setOpen(true)}>
        {children || "Log in"}
      </Button>

      <AuthModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
