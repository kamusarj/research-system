"use client";

import { useI18n } from "@/lib/i18n";

export function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  return <span className={`badge status-${status}`}>{t(`status.${status}`)}</span>;
}
