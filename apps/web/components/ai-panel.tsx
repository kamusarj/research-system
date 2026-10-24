"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

type AIOutput = { id: string; model_name: string; confidence: number; output: { summary?: string; concepts?: string[]; tags?: string[] } };

export function AIPanel({ researchId, onAccepted }: { researchId: string; onAccepted: () => void }) {
  const { t } = useI18n();
  const { can } = useAuth();
  const [suggestion, setSuggestion] = useState<AIOutput | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    try { await task(); } catch (reason) { setError(reason instanceof Error ? reason.message : t("unableSave")); } finally { setBusy(false); }
  }
  const enrich = () => run(async () => { setSuggestion(await api<AIOutput>(`/ai/enrich/${researchId}`, { method: "POST" })); });
  const accept = () => run(async () => {
    if (!suggestion) return;
    await api(`/ai/outputs/${suggestion.id}/accept`, { method: "POST" });
    setSuggestion(null);
    onAccepted();
  });
  return <section className="card"><h2>{t("aiSuggestions")}</h2><p className="muted">{t("aiSeparate")}</p><button onClick={enrich} disabled={busy}>{busy ? t("enriching") : t("summarizeExtract")}</button>{error && <p className="notice error-notice" role="alert">{error}</p>}{suggestion && <div className="suggestion"><p>{suggestion.output.summary}</p><p>{suggestion.output.concepts?.map((concept) => <span className="tag" key={concept}>{concept}</span>)}</p><small className="muted">{suggestion.model_name} · {t("confidence")} {suggestion.confidence}</small><div className="actions">{can("owner") && <button onClick={accept} disabled={busy}>{t("acceptSummaryTags")}</button>}<button className="secondary" onClick={() => setSuggestion(null)}>{t("reject")}</button></div></div>}</section>;
}
