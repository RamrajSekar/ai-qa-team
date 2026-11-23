"use client";

import Link from "next/link";
import { Eye, Pencil, Play, Trash2, Video } from "lucide-react";
import styles from "./icon-action.module.css";

type Action = "view" | "review" | "edit" | "delete" | "remove" | "record" | "recording";
const icons = { view: Eye, review: Eye, edit: Pencil, delete: Trash2, remove: Trash2, record: Play, recording: Video };

export function IconAction({ action, label, href, onClick, disabled = false }: {
  action: Action; label: string; href?: string; onClick?: () => void; disabled?: boolean;
}) {
  const Icon = icons[action];
  const className = `workspace-button ${styles.button} ${action === "delete" || action === "remove" ? "design-danger" : ""}`;
  const icon = <Icon size={17} aria-hidden="true" focusable="false" />;
  return href && !disabled
    ? <Link className={className} href={href} title={label} aria-label={label}>{icon}</Link>
    : <button type="button" className={className} title={label} aria-label={label} disabled={disabled} onClick={onClick}>{icon}</button>;
}
