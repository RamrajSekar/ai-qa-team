"use client";

import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./dialog";
import { cn } from "@/lib/utils";

/** Shared workspace modal: focus trap, Escape, focus restoration and scroll bounds. */
export function WorkspaceDialog({ open, onClose, title, description, className, busy = false, children }: {
  open: boolean; onClose: () => void; title: string; description?: string;
  className?: string; busy?: boolean; children: React.ReactNode;
}) {
  return <Dialog open={open} onOpenChange={value => { if (!value && !busy) onClose(); }}>
    <DialogContent className={cn("workspace-dialog", className)} {...(!description ? { "aria-describedby": undefined } : {})}
      onPointerDownOutside={event => event.preventDefault()}>
      <DialogTitle className="sr-only">{title}</DialogTitle>
      {description && <DialogDescription className="sr-only">{description}</DialogDescription>}
      {children}
    </DialogContent>
  </Dialog>;
}
