"use client";

import { Fragment, type ReactNode, useEffect, useState } from "react";
import { API_URL, apiFetch } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { DocumentContent } from "@/lib/types";

type ViewMode = "raw" | "preview" | "split";

function markdownPreview(source: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const lines = source.split("\n");
  let codeLines: string[] = [];
  let inCode = false;
  lines.forEach((line, index) => {
    if (/^\s*```/.test(line)) {
      if (inCode) {
        nodes.push(<pre key={`code-${index}`}><code>{codeLines.join("\n")}</code></pre>);
        codeLines = [];
        inCode = false;
      } else {
        inCode = true;
      }
      return;
    }
    if (inCode) {
      codeLines.push(line);
      return;
    }
    const heading = /^(#{1,6})\s+(.+)$/.exec(line);
    if (heading) {
      const level = Math.min(heading[1].length + 1, 6);
      const Tag: "h2" | "h3" | "h4" | "h5" | "h6" =
        level <= 2 ? "h2" : level === 3 ? "h3" : level === 4 ? "h4" : level === 5 ? "h5" : "h6";
      nodes.push(<Tag key={`heading-${index}`}>{heading[2]}</Tag>);
      return;
    }
    const listItem = /^\s*(?:[-*+]|\d+\.)\s+(.+)$/.exec(line);
    if (listItem) {
      nodes.push(<div className="source-preview-list-item" key={`item-${index}`}>• {listItem[1]}</div>);
      return;
    }
    const quote = /^\s*>\s?(.+)$/.exec(line);
    if (quote) {
      nodes.push(<blockquote key={`quote-${index}`}>{quote[1]}</blockquote>);
      return;
    }
    if (line.trim()) nodes.push(<p key={`paragraph-${index}`}>{line}</p>);
  });
  if (inCode) nodes.push(<pre key="code-final"><code>{codeLines.join("\n")}</code></pre>);
  return nodes;
}

function latexPreview(source: string): ReactNode[] {
  const start = source.match(/^\s*\\begin\{document\}\s*$/m);
  const body = start
    ? source.slice((start.index ?? 0) + start[0].length).split(/^\s*\\end\{document\}\s*$/m)[0]
    : source;

  return body.split("\n").map((line, index) => {
    const uncommented = line.replace(/(^|[^\\])%.*/, "$1");
    if (!uncommented.trim()) return null;
    const heading = /^\s*\\(chapter|section|subsection|subsubsection)\*?\{([^{}]+)\}/.exec(line);
    if (heading) {
      const Tag = heading[1] === "chapter" || heading[1] === "section" ? "h2" : "h3";
      return <Tag key={`latex-heading-${index}`}>{heading[2]}</Tag>;
    }
    const item = /^\s*\\item\s*(.*)$/.exec(line);
    if (item) {
      return <div className="source-preview-list-item" key={`latex-item-${index}`}>• {item[1]}</div>;
    }
    const sideSection = /^\s*\\sidesection\{([^{}]+)\}\s*$/.exec(uncommented);
    if (sideSection) return <h3 key={`latex-side-section-${index}`}>{sideSection[1]}</h3>;
    const mainSection = /^\s*\\mainsection\{([^{}]+)\}\s*$/.exec(uncommented);
    if (mainSection) return <h2 key={`latex-main-section-${index}`}>{mainSection[1]}</h2>;
    const jobHeading = /^\s*\\jobheading\{([^{}]+)\}\{([^{}]+)\}\{([^{}]+)\}\s*$/.exec(uncommented);
    if (jobHeading) {
      return (
        <Fragment key={`latex-job-heading-${index}`}>
          <h3>{jobHeading[1]}</h3>
          <p>{jobHeading[2]} · {jobHeading[3]}</p>
        </Fragment>
      );
    }
    const skillBar = /^\s*\\skillbar\{([^{}]+)\}\{[^{}]+\}\s*$/.exec(uncommented);
    if (skillBar) return <div className="source-preview-list-item" key={`latex-skill-${index}`}>• {skillBar[1]}</div>;
    if (/^\s*\\(?:tightbullets|closebullets)\s*$/.test(uncommented)) return null;
    const readable = uncommented
      .replace(/\\(?:textbf|textit|emph|underline|textrm|texttt)\{([^{}]*)\}/g, "$1")
      .replace(/\\(?:href\{[^{}]*\}|textcolor\{[^{}]*\})\{([^{}]*)\}/g, "$1")
      .replace(/\\url\{([^{}]*)\}/g, "$1")
      .replace(/\\(?:vspace|hspace)\*?\{[^{}]*\}/g, "")
      .replace(/\\fontsize\{[^{}]*\}\{[^{}]*\}/g, "")
      .replace(/\\(?:documentclass|usepackage|setmainfont|fontspec|pagestyle|setlength|hypersetup|definecolor|pagecolor|color|newcommand|renewcommand|providecommand|title|author|date|includegraphics|rule)\*?(?:\[[^\]]*\])?\{[^{}]*\}(?:\{[^{}]*\})?/g, "")
      .replace(/\\(?:begin|end)\{[^{}]*\}(?:\{[^{}]*\})?/g, "")
      .replace(/\\(?:selectfont|bfseries|mdseries|itshape|slshape|scshape|upshape|normalfont|RaggedRight|raggedright|centering|flushleft|flushright|small|normalsize|large|Large|LARGE|huge|Huge|par)\b/g, "")
      .replace(/\\(?:mainsection|jobheading|sidesection|skillbar|tightbullets|closebullets)\b/g, "")
      .replace(/\\(?:quad|qquad|newline)\b/g, " ")
      .replace(/\\\\/g, " ")
      .replace(/^[\s{}]+|[\s{}]+$/g, "")
      .replace(/\s{2,}/g, " ");
    if (!readable) return <Fragment key={`latex-space-${index}`} />;
    if (/^\s*(?:\$\$|\\\[)/.test(line)) {
      return <pre className="source-formula" key={`latex-math-${index}`}>{readable}</pre>;
    }
    return <p key={`latex-paragraph-${index}`}>{readable}</p>;
  });
}

function LatexPdfPreview({ source }: { source: string }) {
  const { t } = useI18n();
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    setPdfUrl(null);
    const timer = window.setTimeout(async () => {
      try {
        const response = await apiFetch("/documents/latex/compile", {
          method: "POST",
          body: JSON.stringify({ source }),
          signal: controller.signal,
        });
        if (!response.ok) {
          const payload = await response.json().catch(() => null) as
            | { error?: { message?: string } }
            | null;
          throw new Error(payload?.error?.message ?? t("latexCompileFailed"));
        }
        const nextPdfUrl = URL.createObjectURL(await response.blob());
        if (controller.signal.aborted) {
          URL.revokeObjectURL(nextPdfUrl);
          return;
        }
        setPdfUrl(nextPdfUrl);
      } catch (reason) {
        if (controller.signal.aborted) return;
        setPdfUrl(null);
        setError(reason instanceof Error ? reason.message : t("latexCompileFailed"));
      }
    }, 450);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [source, t]);

  useEffect(() => () => {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
  }, [pdfUrl]);

  if (pdfUrl) {
    return (
      <iframe
        className="latex-pdf-preview"
        src={`${pdfUrl}#toolbar=0&navpanes=0&view=Fit`}
        title={t("compiledLatexPreview")}
      />
    );
  }
  return (
    <>
      <div className={`latex-compile-status${error ? " error" : ""}`} role="status">
        {error ? `${t("latexCompileFailed")}: ${error}` : t("latexCompiling")}
      </div>
      {latexPreview(source)}
    </>
  );
}

function plainPreview(source: string): ReactNode[] {
  return source.split(/\n{2,}/).filter(Boolean).map((paragraph, index) => (
    <p key={`plain-${index}`}>{paragraph}</p>
  ));
}

export function DocumentPreview({ content }: { content: DocumentContent }) {
  const source = (
    ["markdown", "latex", "markup"].includes(content.preview_kind)
      ? content.source_text
      : content.extracted_text
  ) || content.extracted_text || content.source_text || "";
  if (!source) return <div className="table-state">{content.filename}</div>;
  if (content.preview_kind === "markdown" || content.preview_kind === "markup") {
    return <>{markdownPreview(source)}</>;
  }
  if (content.preview_kind === "latex") return <LatexPdfPreview source={source} />;
  return <>{plainPreview(source)}</>;
}

export function DocumentOriginalViewer({ content }: { content: DocumentContent }) {
  const { t } = useI18n();
  if (!content.original_available) return null;
  const originalUrl = `${API_URL}/documents/${content.workspace_id}/original`;
  return (
    <details className="document-original-file" open={content.original_preview_kind === "pdf"}>
      <summary>{t("originalUploadedFile")}</summary>
      <div className="document-original-file-body">
        <div>
          <p className="muted">{t("originalFilePreservedHint")}</p>
          <a className="button-link secondary" href={originalUrl}>{t("downloadOriginal")}</a>
        </div>
        {content.original_preview_kind === "pdf" && (
          <iframe
            className="document-original-pdf"
            src={`${originalUrl}?inline=true#toolbar=1&navpanes=0&view=Fit`}
            title={t("originalPdfPreview")}
          />
        )}
      </div>
    </details>
  );
}

export function DocumentSourceViewer({
  content,
  collapsible = false,
}: {
  content: DocumentContent;
  collapsible?: boolean;
}) {
  const { t } = useI18n();
  const [mode, setMode] = useState<ViewMode>(content.supports_raw ? "split" : "preview");
  const raw = content.source_text ?? content.extracted_text;

  const viewer = (
    <>
      <DocumentOriginalViewer content={content} />
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">{t("documentContent")}</p>
          <h2>{t("sourceAndPreview")}</h2>
          <p className="muted">{t("sourcePreviewHint")}</p>
        </div>
        <div className="source-view-switcher" aria-label={t("documentViewMode")}>
          {content.supports_raw && (
            <button type="button" className={mode === "raw" ? "active" : ""} aria-pressed={mode === "raw"} onClick={() => setMode("raw")}>
              {t("rawView")}
            </button>
          )}
          <button type="button" className={mode === "preview" ? "active" : ""} aria-pressed={mode === "preview"} onClick={() => setMode("preview")}>
            {t("previewView")}
          </button>
          {content.supports_raw && (
            <button type="button" className={mode === "split" ? "active" : ""} aria-pressed={mode === "split"} onClick={() => setMode("split")}>
              {t("sideBySideView")}
            </button>
          )}
        </div>
      </div>
      {content.source_truncated && <p className="notice">{t("rawContentTruncated")}</p>}
      <div className={`document-source-view mode-${mode}`}>
        {(mode === "raw" || mode === "split") && (
          <article className="source-raw-pane">
            <h3>{t("rawSource")}</h3>
            <pre><code>{raw}</code></pre>
          </article>
        )}
        {(mode === "preview" || mode === "split") && (
          <article className="source-preview-pane">
            <h3>{t("formattedPreview")}</h3>
            <div className="document-rendered-preview">
              <div className="document-preview-paper"><DocumentPreview content={content} /></div>
            </div>
          </article>
        )}
      </div>
    </>
  );

  if (collapsible) {
    return (
      <details className="document-preview-disclosure">
        <summary>{t("previewDocument")}</summary>
        <div className="document-preview-disclosure-body">{viewer}</div>
      </details>
    );
  }

  return (
    <section className="card document-source-panel">
      {viewer}
    </section>
  );
}
