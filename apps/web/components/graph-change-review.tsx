"use client";

import { useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { graphTypeLabel } from "@/lib/knowledge-graph/graph-theme";
import { decideGraphMutation } from "@/lib/graph-changes";
import { useI18n } from "@/lib/i18n";
import type { GraphMutation, OntologyCandidate } from "@/lib/types";

const operationLabels: Record<string, string> = {
  CREATE_NODE: "Tạo nút",
  UPDATE_NODE: "Cập nhật nút",
  CREATE_EDGE: "Tạo cạnh",
  UPDATE_EDGE: "Cập nhật cạnh",
  DELETE_NODE: "Xóa nút",
  DELETE_EDGE: "Xóa cạnh",
};

const validationLabels: Record<string, string> = {
  EVIDENCE_REQUIRED: "Cần có bằng chứng trước khi áp dụng thay đổi.",
  INVALID_LABEL: "Nhãn đề xuất chưa hợp lệ.",
  INVALID_NODE_TYPE: "Loại nút đề xuất chưa hợp lệ.",
  PARENT_REQUIRED: "Cần chọn nút cha cho đề xuất này.",
  PARENT_NOT_FOUND: "Không tìm thấy nút cha đã chọn.",
  ONTOLOGY_PLACEMENT_CONFLICT: "Vị trí đề xuất xung đột với cấu trúc tri thức hiện tại.",
  DUPLICATE_NODE_CANDIDATE: "Có một nút chuẩn có khả năng bị trùng.",
  SIMILAR_NODE_CANDIDATE: "Có nút chuẩn tương tự cần được kiểm tra.",
  TARGET_NOT_FOUND: "Không tìm thấy đối tượng cần thay đổi.",
  EDGE_TARGET_NOT_FOUND: "Không tìm thấy nút đích của cạnh.",
  SELF_LOOP: "Một nút không thể tạo quan hệ với chính nó theo cách này.",
  INVALID_EDGE_TYPE: "Loại cạnh đề xuất chưa hợp lệ.",
  INVALID_CONFIDENCE: "Độ tin cậy phải nằm trong khoảng hợp lệ.",
  RELATION_TYPE_REVIEW: "Cần kiểm tra lại loại quan hệ trước khi áp dụng.",
  INVALID_ALIAS: "Tên thay thế đề xuất chưa hợp lệ.",
  UNSUPPORTED_MUTATION: "Loại thay đổi này chưa được hỗ trợ.",
  HIERARCHY_CYCLE: "Thay đổi này sẽ tạo vòng lặp trong cấu trúc phân cấp.",
};

export function GraphChangeReview({
  changeSetId,
  mutation,
  editable,
  onChanged,
}: {
  changeSetId: string;
  mutation: GraphMutation;
  editable: boolean;
  onChanged: () => Promise<unknown>;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState<Record<string, unknown>>(mutation.proposed_json);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const candidates = (draft.candidates ?? []) as OntologyCandidate[];
  const evidence = (draft.evidence_preview ?? []) as Array<{
    id: string;
    excerpt: string | null;
    location: Record<string, unknown>;
  }>;
  const sourceLabel = String(
    draft.source_label ?? draft.canonical_label ?? draft.original_edge_type ?? draft.source_node_id ?? "—",
  );
  const targetLabel = String(
    draft.target_label ?? draft.canonical_label ?? draft.edge_type ?? draft.target_node_id ?? mutation.target_id ?? "—",
  );

  function update(name: string, value: string) {
    setDraft((current) => ({ ...current, [name]: value }));
  }

  async function decide(decision: "accepted" | "rejected") {
    setSaving(true);
    setError(null);
    try {
      await decideGraphMutation(
        changeSetId,
        mutation.id,
        decision,
        decision === "accepted" ? draft : undefined,
      );
      await onChanged();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("actionFailed"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className={`change-mutation-card decision-${mutation.review_decision}`}>
      <header>
        <div>
          <p className="eyebrow">#{mutation.mutation_order + 1} · {operationLabels[mutation.operation] ?? "Thay đổi đồ thị"}</p>
          <h3>{targetLabel}</h3>
        </div>
        <div className="mutation-statuses">
          <StatusBadge status={mutation.validation_status} />
          <StatusBadge status={mutation.review_decision} />
        </div>
      </header>

      <div className="change-diff-grid">
        <div><span>{t("sourceProposal")}</span><strong>{sourceLabel}</strong></div>
        <span aria-hidden="true">→</span>
        <div><span>{t("canonicalResult")}</span><strong>{targetLabel}</strong></div>
      </div>

      {mutation.operation === "CREATE_NODE" && (
        <div className="mutation-edit-grid">
          <label>{t("canonicalLabel")}<input value={String(draft.canonical_label ?? "")} disabled={!editable} onChange={(event) => update("canonical_label", event.target.value)} /></label>
          <label>{t("nodeType")}<input value={String(draft.node_type ?? "")} disabled={!editable} onChange={(event) => update("node_type", event.target.value)} /></label>
          <label className="wide">{t("displayParentId")}<input value={String(draft.primary_parent_id ?? "")} disabled={!editable} onChange={(event) => update("primary_parent_id", event.target.value)} /></label>
        </div>
      )}
      {mutation.operation === "CREATE_EDGE" && (
        <div className="mutation-edit-grid">
          <label>{t("edgeType")}<input value={String(draft.edge_type ?? "")} disabled={!editable} onChange={(event) => update("edge_type", event.target.value)} /></label>
          <label>{t("confidence")}<input value={String(draft.confidence ?? "")} disabled readOnly /></label>
        </div>
      )}

      {candidates.length > 0 && (
        <div className="candidate-comparison">
          <strong>{t("similarCandidates")}</strong>
          {candidates.map((candidate) => (
            <div key={candidate.node_id}>
              <span>{candidate.canonical_label}<small>{graphTypeLabel(candidate.node_type)}</small></span>
              <b>{Math.round(candidate.score * 100)}%</b>
            </div>
          ))}
        </div>
      )}

      {evidence.length > 0 && (
        <div className="mutation-evidence">
          <strong>{t("evidenceContext")}</strong>
          {evidence.map((item) => (
            <blockquote key={item.id}>
              <p>{item.excerpt ?? t("noExtractedPreview")}</p>
              <small>{Object.entries(item.location).map(([key, value]) => `${key}: ${String(value)}`).join(" · ")}</small>
            </blockquote>
          ))}
        </div>
      )}

      {mutation.validation_messages.length > 0 && (
        <ul className="mutation-messages">
          {mutation.validation_messages.map((message) => (
            <li className={message.level} key={`${message.code}-${message.message}`}>
              <strong>{message.code}</strong> {validationLabels[message.code] ?? "Cần kiểm tra thay đổi này trước khi áp dụng."}
            </li>
          ))}
        </ul>
      )}
      {error && <p className="notice error-notice">{error}</p>}
      {editable && (
        <footer>
          <button disabled={saving} onClick={() => decide("accepted")}>{t("acceptMutation")}</button>
          <button className="secondary" disabled={saving} onClick={() => decide("rejected")}>{t("rejectMutation")}</button>
        </footer>
      )}
    </article>
  );
}
