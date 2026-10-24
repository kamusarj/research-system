"use client";

import { useI18n } from "@/lib/i18n";

type Props = {
  code: string | null | undefined;
  message: string | null | undefined;
  details?: Record<string, unknown> | null;
};

/**
 * Explain a failed submission in the reader's language and say what to do next.
 *
 * Mã lỗi vẫn được giữ để hỗ trợ vận hành, nhưng thông báo thô từ máy chủ không
 * được đưa ra giao diện vì dữ liệu cũ có thể dùng ngôn ngữ khác.
 */
export function SubmissionError({ code, message, details }: Props) {
  const { t } = useI18n();
  if (!code && !message) return null;

  const titleKey = `error.${code}`;
  const hintKey = `errorHint.${code}`;
  const translatedTitle = code ? t(titleKey) : "";
  const translatedHint = code ? t(hintKey) : "";
  const title = translatedTitle && translatedTitle !== titleKey
    ? translatedTitle
    : "Không thể xử lý nguồn này";
  const hint = translatedHint && translatedHint !== hintKey ? translatedHint : "";

  return (
    <div className="submission-error" role="alert">
      <p className="submission-error-title">{title}</p>
      {hint && (
        <p className="submission-error-hint">
          <strong>{t("whatToDo")}:</strong> {hint}
        </p>
      )}
      <p className="submission-error-meta">
        <code>{code}</code>
        {typeof details?.content_type === "string" && <span> · {details.content_type}</span>}
        {typeof details?.status_code === "number" && <span> · HTTP {details.status_code}</span>}
      </p>
    </div>
  );
}
