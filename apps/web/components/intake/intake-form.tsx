"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { PartialIntakeError, detectSourceKind, parseUrls } from "@/lib/intake";
import { useI18n } from "@/lib/i18n";
import type { Provider, SourceSubmission } from "@/lib/types";

type Props = {
  providers: Provider[];
  onSubmit: (urls: string[], provider: string) => Promise<SourceSubmission[]>;
};

export function IntakeForm({ providers, onSubmit }: Props) {
  const { t } = useI18n();
  const [value, setValue] = useState("");
  const [provider, setProvider] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const urls = useMemo(() => parseUrls(value), [value]);

  useEffect(() => {
    const available = providers.filter(
      (item) => item.configured && item.reachable !== false,
    );
    setProvider((current) => {
      if (available.some((item) => item.id === current)) return current;
      return available.find((item) => item.active)?.id ?? available[0]?.id ?? "";
    });
  }, [providers]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!urls.length) return;
    setWorking(true);
    setError("");
    try {
      await onSubmit(urls, provider);
      setValue("");
    } catch (reason) {
      // Liên kết đã gửi thành công được bỏ khỏi ô nhập để không bị gửi lại thành bản trùng.
      if (reason instanceof PartialIntakeError) setValue(reason.failedUrls.join("\n"));
      setError(reason instanceof Error ? reason.message : t("submissionFailed"));
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="intake-panel" aria-labelledby="add-sources-title">
      <div className="section-heading compact">
        <div>
          <h2 id="add-sources-title">{t("addSources")}</h2>
          <p className="muted">{t("multiUrlHint")}</p>
        </div>
        <span>{urls.length}</span>
      </div>
      <form onSubmit={submit} className="intake-form">
        <label className="url-field">
          <span>{t("url")}</span>
          <textarea
            rows={5}
            placeholder={"https://github.com/…\nhttps://arxiv.org/abs/…\nhttps://example.com/report.pdf"}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            required
          />
        </label>
        <div className="intake-options">
          <label>
            <span>{t("provider")}</span>
            <select value={provider} onChange={(event) => setProvider(event.target.value)}>
              {!provider && <option value="">{t("unavailable")}</option>}
              {providers.map((item) => (
                <option key={item.id} value={item.id} disabled={!item.configured || item.reachable === false}>
                  {item.id} · {item.model} ({!item.configured ? t("unavailable") : item.reachable === false ? t("unreachable") : t("configured")})
                </option>
              ))}
            </select>
          </label>
          <button disabled={working || urls.length === 0 || !provider}>
            {working ? t("submittingSources") : t("submitSources")}
          </button>
        </div>
      </form>
      {urls.length > 0 && (
        <div className="source-preview" aria-label={t("detectedSources")}>
          {urls.map((url) => (
            <div key={url}>
              <span className={`source-kind source-${detectSourceKind(url)}`}>
                {t(`sourceType.${detectSourceKind(url)}`)}
              </span>
              <span title={url}>{url}</span>
            </div>
          ))}
        </div>
      )}
      {error && <p className="notice error-notice" role="alert">{error}</p>}
    </section>
  );
}
