"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { Research } from "@/lib/types";

export function ResearchForm({ item, onSaved }: { item?: Research; onSaved?: (item: Research) => void }) {
  const { t } = useI18n();
  const [title, setTitle] = useState(item?.title ?? "");
  const [summary, setSummary] = useState(item?.summary ?? "");
  const [content, setContent] = useState(item?.content ?? "");
  const [tags, setTags] = useState(item?.tags.join(", ") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const saved = await api<Research>(item ? `/research/${item.id}` : "/research", {
        method: item ? "PUT" : "POST",
        body: JSON.stringify({ title, summary: summary || null, content, tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean), ...(item ? {} : { type: "internal-research", collection_method: "manual" }) }),
      });
      onSaved?.(saved);
      if (!item) { setTitle(""); setSummary(""); setContent(""); setTags(""); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : t("unableSave")); }
    finally { setBusy(false); }
  }

  return <form className="form card" onSubmit={submit}><label>{t("title")}<input value={title} onChange={(e) => setTitle(e.target.value)} required /></label><label>{t("summary")}<textarea rows={3} value={summary} onChange={(e) => setSummary(e.target.value)} /></label><label>{t("markdownContent")}<textarea className="editor" rows={12} value={content} onChange={(e) => setContent(e.target.value)} /></label><label>{t("tagsComma")}<input value={tags} onChange={(e) => setTags(e.target.value)} /></label>{error && <p className="error">{error}</p>}<button disabled={busy}>{busy ? t("saving") : item ? t("saveVersion") : t("createDraft")}</button></form>;
}
