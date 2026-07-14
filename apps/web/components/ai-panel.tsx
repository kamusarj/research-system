"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type AIOutput = { id: string; model_name: string; confidence: number; output: { summary?: string; concepts?: string[]; tags?: string[] } };

export function AIPanel({ researchId, onAccepted }: { researchId: string; onAccepted: () => void }) {
  const { t } = useI18n();
  const [suggestion, setSuggestion] = useState<AIOutput | null>(null);
  const [busy, setBusy] = useState(false);
  async function enrich() { setBusy(true); try { setSuggestion(await api<AIOutput>(`/ai/enrich/${researchId}`, { method: "POST" })); } finally { setBusy(false); } }
  async function accept() { if (!suggestion) return; await api(`/ai/outputs/${suggestion.id}/accept`, { method: "POST" }); setSuggestion(null); onAccepted(); }
  return <section className="card"><h2>{t("aiSuggestions")}</h2><p className="muted">{t("aiSeparate")}</p><button onClick={enrich} disabled={busy}>{busy ? t("enriching") : t("summarizeExtract")}</button>{suggestion && <div className="suggestion"><p>{suggestion.output.summary}</p><p>{suggestion.output.concepts?.map((concept) => <span className="tag" key={concept}>{concept}</span>)}</p><small className="muted">{suggestion.model_name} · {t("confidence")} {suggestion.confidence}</small><div className="actions"><button onClick={accept}>{t("acceptSummaryTags")}</button><button className="secondary" onClick={() => setSuggestion(null)}>{t("reject")}</button></div></div>}</section>;
}
