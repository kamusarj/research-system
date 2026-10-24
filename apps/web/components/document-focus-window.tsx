"use client";

import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { useI18n } from "@/lib/i18n";

export function DocumentFocusWindow({
  open,
  title,
  onClose,
  left,
  right,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  left: ReactNode;
  right: ReactNode;
}) {
  const { t } = useI18n();

  useEffect(() => {
    if (!open) return;
    function keyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", keyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", keyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div className="document-focus-window" role="dialog" aria-modal="true" aria-label={title}>
      <header className="document-focus-window-header">
        <h2>{title}</h2>
        <button
          type="button"
          className="document-focus-window-close"
          aria-label={t("closeFocusWindow")}
          onClick={onClose}
        >
          ✕
        </button>
      </header>
      <div className="document-focus-window-body">
        <section className="document-focus-window-pane document-focus-window-text">
          {left}
        </section>
        <section className="document-focus-window-pane document-focus-window-chat" aria-label={t("documentWindowChat")}>
          {right}
        </section>
      </div>
    </div>,
    document.body,
  );
}
