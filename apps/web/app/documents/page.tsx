"use client";

import Link from "next/link";
import { type FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DocumentAuthoring } from "@/components/document-authoring";
import { Pager } from "@/components/pager";
import { api, API_URL } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  DOCUMENT_MAX_UPLOAD_BYTES,
  deleteDocument,
  formatDocumentBytes,
  uploadDocument,
} from "@/lib/documents";
import { useI18n } from "@/lib/i18n";
import type { DocumentWorkspaceList } from "@/lib/types";

const PAGE_SIZE = 50;

export default function DocumentsPage() {
  const { t } = useI18n();
  const { can, user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [documentMessage, setDocumentMessage] = useState<{
    type: "error" | "success";
    text: string;
  } | null>(null);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(
    null,
  );
  const documents = useQuery({
    queryKey: ["document-workspaces", page],
    queryFn: () => api<DocumentWorkspaceList>(
      `/documents?limit=${PAGE_SIZE}&offset=${(page - 1) * PAGE_SIZE}`,
    ),
    refetchInterval: (query) => query.state.data?.items.some((item) =>
      ["uploaded", "queued", "processing", "extracting", "evaluating", "graph_building"].includes(item.processing_status)
    ) ? 2000 : false,
  });

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    if (file.size > DOCUMENT_MAX_UPLOAD_BYTES) {
      setMessage({ type: "error", text: t("documentTooLarge") });
      return;
    }
    setUploading(true);
    setMessage(null);
    try {
      await uploadDocument(file);
      setFile(null);
      setMessage({ type: "success", text: t("documentUploaded") });
      await documents.refetch();
    } catch (reason) {
      setMessage({
        type: "error",
        text: reason instanceof Error ? reason.message : t("documentUploadFailed"),
      });
    } finally {
      setUploading(false);
    }
  }

  async function removeDocument(id: string, filename: string) {
    if (!window.confirm(t("confirmDeleteDocument").replace("{filename}", filename))) return;
    setDeletingId(id);
    setDocumentMessage(null);
    try {
      await deleteDocument(id);
      setDocumentMessage({ type: "success", text: t("documentDeleted") });
      await documents.refetch();
    } catch (reason) {
      setDocumentMessage({
        type: "error",
        text: reason instanceof Error ? reason.message : t("documentDeleteFailed"),
      });
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <>
      <header className="page-header document-page-header">
        <div>
          <h1>{t("documentWorkspace")}</h1>
        </div>
      </header>

      {can("researcher") && user && <DocumentAuthoring userId={user.id} />}

      {can("researcher") && <details className="card document-upload-disclosure">
        <summary>{t("uploadBinaryDocument")}</summary>
        <form className="document-upload-card compact" onSubmit={submit}>
          <div>
            <h2>{t("chooseBinaryResearchFile")}</h2>
          </div>
          <label className="document-file-field">
            <span>{file ? file.name : t("chooseFile")}</span>
            <input
              key={file ? file.name : "empty"}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          {file && (
            <div className="document-file-meta">
              <span>{file.type || t("unknownMime")}</span>
              <strong>{formatDocumentBytes(file.size)}</strong>
            </div>
          )}
          <button type="submit" disabled={!file || uploading}>
            {uploading ? t("uploadingDocument") : t("uploadDocument")}
          </button>
          {message && (
            <p className={`notice ${message.type === "error" ? "error-notice" : "document-success"}`}>
              {message.text}
            </p>
          )}
        </form>
      </details>}

      <div className="section-heading">
        <div><h2>{t("uploadedDocuments")}</h2></div>
        <span>{documents.data?.total ?? 0}</span>
      </div>
      {documentMessage && (
        <p className={`notice ${documentMessage.type === "error" ? "error-notice" : "document-success"}`}>
          {documentMessage.text}
        </p>
      )}
      {documents.error && <p className="notice error-notice">{documents.error.message}</p>}
      <div className="data-table document-workspace-table">
        <div className="table-header">
          <span>{t("document")}</span><span>{t("documentSummary")}</span><span>{t("size")}</span><span>{t("actionsLabel")}</span>
        </div>
        {documents.data?.items.map((item) => (
          <div className="table-row" key={item.id}>
            <div className="document-cell">
              <Link className="document-title" href={`/documents/${item.id}`}>
                {item.filename}
              </Link>
            </div>
            <p className={`document-summary-cell${item.summary ? "" : " muted"}`}>
              {item.summary || t("noDocumentSummary")}
            </p>
            <span>{formatDocumentBytes(item.size_bytes)}</span>
            <div className="document-row-actions">
              <Link className="text-link" href={`/documents/${item.id}`}>{t("editDocument")}</Link>
              <Link className="text-link" href={`/documents/${item.id}#document-analysis`}>
                {t("viewAnalysis")}
              </Link>
              <a className="text-link" href={`${API_URL}/documents/${item.id}/download`}>
                {t("download")}
              </a>
              <Link className="text-link" href={`/research/${item.research_id}`}>{t("openResearch")}</Link>
              {can("owner") && (
                <button
                  className="document-delete-action"
                  type="button"
                  disabled={deletingId === item.id}
                  onClick={() => void removeDocument(item.id, item.filename)}
                >
                  {deletingId === item.id ? t("deletingDocument") : t("deleteDocument")}
                </button>
              )}
            </div>
          </div>
        ))}
        {documents.isLoading && <div className="table-state"><span className="spinner" />{t("loading")}</div>}
        {!documents.isLoading && documents.data?.items.length === 0 && (
          <div className="table-state"><strong>{t("noUploadedDocuments")}</strong></div>
        )}
      </div>
      {documents.data && (
        <Pager page={page} pageSize={PAGE_SIZE} total={documents.data.total} onChange={setPage} />
      )}
    </>
  );
}
