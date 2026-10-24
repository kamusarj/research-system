"use client";

import { createPortal } from "react-dom";
import { type ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";

export type SelectionAnchor = {
  left: number;
  top: number;
  right: number;
  bottom: number;
};

type Position = { left: number; top: number };

const VIEWPORT_GAP = 10;

export function selectionAnchorFromRect(rect: Pick<DOMRect, "left" | "top" | "right" | "bottom">): SelectionAnchor {
  return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom };
}

export function textareaSelectionAnchor(
  textarea: HTMLTextAreaElement,
  selectionEnd: number,
): SelectionAnchor {
  const textareaRect = textarea.getBoundingClientRect();
  const styles = window.getComputedStyle(textarea);
  const mirror = document.createElement("div");
  const marker = document.createElement("span");
  const copiedProperties = [
    "boxSizing", "width", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft",
    "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth",
    "fontFamily", "fontSize", "fontStyle", "fontWeight", "letterSpacing", "lineHeight",
    "textAlign", "textIndent", "textTransform", "tabSize", "wordSpacing",
  ] as const;

  mirror.setAttribute("aria-hidden", "true");
  mirror.style.position = "fixed";
  mirror.style.left = `${textareaRect.left}px`;
  mirror.style.top = `${textareaRect.top}px`;
  mirror.style.visibility = "hidden";
  mirror.style.whiteSpace = "pre-wrap";
  mirror.style.overflowWrap = "break-word";
  mirror.style.pointerEvents = "none";
  copiedProperties.forEach((property) => {
    mirror.style[property] = styles[property];
  });
  mirror.textContent = textarea.value.slice(0, selectionEnd);
  marker.textContent = "\u200b";
  mirror.append(marker);
  document.body.append(mirror);

  const markerRect = marker.getBoundingClientRect();
  mirror.remove();
  const lineHeight = Number.parseFloat(styles.lineHeight) || 20;
  const left = markerRect.left - textarea.scrollLeft;
  const top = markerRect.top - textarea.scrollTop;
  if (
    !Number.isFinite(left)
    || !Number.isFinite(top)
    || top < textareaRect.top
    || top > textareaRect.bottom
  ) {
    const center = textareaRect.left + textareaRect.width / 2;
    return { left: center, right: center, top: textareaRect.top + 56, bottom: textareaRect.top + 56 };
  }
  return { left, right: left + 1, top, bottom: top + lineHeight };
}

export function SelectionActionPopover({
  anchor,
  label,
  children,
  onDismiss,
}: {
  anchor: SelectionAnchor;
  label: string;
  children: ReactNode;
  onDismiss: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<Position | null>(null);

  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const rect = element.getBoundingClientRect();
    const preferredLeft = (anchor.left + anchor.right) / 2 - rect.width / 2;
    const left = Math.min(
      Math.max(VIEWPORT_GAP, preferredLeft),
      Math.max(VIEWPORT_GAP, window.innerWidth - rect.width - VIEWPORT_GAP),
    );
    const above = anchor.top - rect.height - 10;
    const top = above >= VIEWPORT_GAP
      ? above
      : Math.min(anchor.bottom + 10, window.innerHeight - rect.height - VIEWPORT_GAP);
    setPosition({ left, top: Math.max(VIEWPORT_GAP, top) });
  }, [anchor]);

  useEffect(() => {
    function pointerDown(event: PointerEvent) {
      if (!ref.current?.contains(event.target as Node)) onDismiss();
    }
    function keyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onDismiss();
    }
    function viewportChanged() {
      onDismiss();
    }
    document.addEventListener("pointerdown", pointerDown);
    document.addEventListener("keydown", keyDown);
    window.addEventListener("resize", viewportChanged);
    window.addEventListener("scroll", viewportChanged, true);
    return () => {
      document.removeEventListener("pointerdown", pointerDown);
      document.removeEventListener("keydown", keyDown);
      window.removeEventListener("resize", viewportChanged);
      window.removeEventListener("scroll", viewportChanged, true);
    };
  }, [onDismiss]);

  return createPortal(
    <div
      ref={ref}
      className="selection-action-popover"
      role="toolbar"
      aria-label={label}
      style={{
        left: position?.left ?? anchor.left,
        top: position?.top ?? anchor.top,
        visibility: position ? "visible" : "hidden",
      }}
      onMouseDown={(event) => event.preventDefault()}
    >
      {children}
    </div>,
    document.body,
  );
}
