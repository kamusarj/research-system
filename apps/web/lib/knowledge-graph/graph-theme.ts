/**
 * One colour per node type, shared by every surface that draws the graph.
 *
 * The hierarchy view speaks in ontology types (SystemRoot, SystemPillar, Concept) and the
 * relationship view in projection types (ResearchItem, Technology, Person). Both are listed
 * here so the legend, the canvas and the inspector cannot drift apart.
 */

export const graphColors: Record<string, string> = {
  // Ontology hierarchy
  SystemRoot: "#38bdf8",
  SystemPillar: "#818cf8",
  Concept: "#a78bfa",
  Technology: "#2dd4bf",
  AgentPattern: "#818cf8",
  BusinessDomain: "#fbbf24",
  EvidenceClaim: "#f472b6",
  Method: "#22d3ee",
  Dataset: "#c084fc",
  Metric: "#fbbf24",
  Finding: "#4ade80",
  Limitation: "#fb7185",
  Citation: "#94a3b8",
  // Relationship projection
  ResearchItem: "#22d3ee",
  Person: "#94a3b8",
  CollectorSource: "#60a5fa",
  ResearchGap: "#fb7185",
  Source: "#60a5fa",
  Repository: "#4ade80",
  Article: "#34d399",
  Reel: "#fb7185",
  PDF: "#c084fc",
  Claim: "#f472b6",
};

export const fallbackGraphColor = "#94a3b8";

const defaultGraphTypeLabels: Record<string, string> = {
  SystemRoot: "Gốc hệ thống",
  SystemPillar: "Trụ cột hệ thống",
  Concept: "Khái niệm",
  Technology: "Công nghệ",
  AgentPattern: "Mẫu tác nhân AI",
  BusinessDomain: "Lĩnh vực kinh doanh",
  EvidenceClaim: "Luận điểm có bằng chứng",
  Method: "Phương pháp",
  Dataset: "Bộ dữ liệu",
  Metric: "Chỉ số",
  Finding: "Phát hiện",
  Limitation: "Hạn chế",
  Citation: "Trích dẫn",
  ResearchItem: "Hồ sơ nghiên cứu",
  Person: "Tác giả",
  CollectorSource: "Nguồn thu thập",
  ResearchGap: "Khoảng trống tri thức",
  Source: "Nguồn",
  Repository: "Kho mã nguồn",
  Article: "Bài viết",
  Reel: "Video ngắn",
  Claim: "Luận điểm",
};

/**
 * Turn a node type into something readable.
 *
 * Type names are PascalCase identifiers, and showing them raw in the legend leaks the data
 * model into the interface. A caller with translations passes them in; without them the
 * identifier is at least split into words.
 */
export function graphTypeLabel(type: string, translations?: Record<string, string>): string {
  const translated = translations?.[type] ?? defaultGraphTypeLabels[type];
  if (translated) return translated;
  return type.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
}

const graphRelationshipLabels: Record<string, string> = {
  PARENT_OF: "Quan hệ cha-con",
  BROADER_THAN: "Khái niệm rộng hơn",
  RESEARCHES: "Nghiên cứu",
  USES_TECH: "Sử dụng công nghệ",
  IMPLEMENTS_PATTERN: "Áp dụng mẫu",
  APPLIES_TO: "Áp dụng cho",
  AUTHORED_BY: "Do tác giả",
  COLLECTED_FROM: "Thu thập từ",
  REFERENCES: "Tham chiếu",
  EXTENDS: "Mở rộng",
  SUPPORTS: "Ủng hộ",
  CONTRADICTS: "Mâu thuẫn",
  FILLS_GAP: "Lấp khoảng trống",
  SYNTHESIZED_INTO: "Tổng hợp thành",
  RELATED_TO: "Liên quan",
  EVIDENCE_FOR: "Bằng chứng cho",
  CITES: "Trích dẫn",
  MENTIONS: "Đề cập",
};

export function graphRelationshipLabel(type: string): string {
  return graphRelationshipLabels[type] ?? type.replaceAll("_", " ").toLocaleLowerCase("vi-VN");
}
