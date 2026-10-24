"use client";

import { useEffect, useState } from "react";
import {
  applyThemePreference,
  nextThemePreference,
  readThemePreference,
  type ThemePreference,
} from "@/lib/theme";

const LABELS: Record<ThemePreference, string> = {
  system: "Giao diện theo hệ thống",
  light: "Giao diện sáng",
  dark: "Giao diện tối",
};

function ThemeIcon({ preference }: { preference: ThemePreference }) {
  const common = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true };
  if (preference === "light") return <svg {...common}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>;
  if (preference === "dark") return <svg {...common}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" /></svg>;
  return <svg {...common}><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></svg>;
}

export function ThemeToggle() {
  // Trạng thái đầu tiên giống nhau ở server và client; lựa chọn đã lưu được đọc sau khi gắn.
  const [preference, setPreference] = useState<ThemePreference>("system");
  useEffect(() => setPreference(readThemePreference()), []);

  function cycle() {
    const next = nextThemePreference(preference);
    applyThemePreference(next);
    setPreference(next);
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={cycle}
      aria-label={`${LABELS[preference]}. Bấm để đổi`}
      title={LABELS[preference]}
    >
      <ThemeIcon preference={preference} />
    </button>
  );
}
