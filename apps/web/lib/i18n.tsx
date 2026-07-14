"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

export type Locale = "en" | "vi";

const messages: Record<Locale, Record<string, string>> = {
  en: {
    submissionQueued: "Link queued for processing. Its status will update automatically.", existingSubmission: "This URL already exists",
    "status.queued": "queued", "status.extracting": "processing", "status.retrying": "waiting to retry", "status.needs-review": "needs review", "status.needs-transcript": "needs transcript", "status.needs-text-layer": "needs PDF text layer", "status.dead-letter": "needs intervention", "status.failed": "failed", "status.duplicate": "duplicate",
    dashboard: "Dashboard", research: "Research", search: "Search", graph: "Knowledge graph",
    gaps: "Knowledge gaps", intake: "Link intake", collector: "Collector", training: "Training data",
    workspace: "Research intelligence workspace", headline: "Turn scattered links into connected knowledge.",
    intro: "Collect, review, enrich and map trustworthy research about AI agents for business.",
    openIntake: "Submit a link", exploreGraph: "Explore graph", systemFlow: "System flow",
    flowText: "Link → extract → classify → review → publish → graph", language: "Language",
    graphTitle: "Interactive knowledge graph", graphIntro: "Explore typed entities and the evidence that connects them.",
    allTypes: "All node types", findNode: "Find a node…", fit: "Fit view", relayout: "Re-layout",
    selectNode: "Select a node to inspect its connections.", connections: "direct connections",
    nodes: "nodes", edges: "edges", clusters: "clusters", legend: "Legend", loading: "Loading…",
    graphProjection: "Graph projection", nodeInspector: "Node inspector", submissionFailed: "Submission failed",
    reset: "Reset", graphProvider: "Graph data provider", graphTruncated: "The result was truncated to keep the graph responsive.",
    graphExpandFailed: "Unable to expand this node.", graphLoadFailed: "Unable to load the knowledge graph",
    graphEmpty: "No published knowledge matches this view", graphEmptyHint: "Publish reviewed research or reset the active filters.",
    topics: "Topics", noTopics: "No topics in this view.", filters: "Filters", nodeTypes: "Node types", timeRange: "Time range",
    evidence: "Evidence", relatedEvidence: "Related documents & evidence",
    intakeTitle: "Link intake & review", intakeIntro: "The stable API contract that manual tools and a future Discord bot will use.",
    url: "Public URL", provider: "AI provider", submit: "Extract & classify", inbox: "Intake inbox",
    source: "Source", confidence: "Confidence", relevance: "Relevance", approve: "Approve & publish",
    reject: "Reject", retry: "Retry", openResearch: "Open research", noLinks: "No submitted links yet.",
    configured: "configured", unavailable: "key required", status: "Status",
    needsTranscriptHint: "Facebook Reel collection is paused safely. Add a transcript with timestamps before AI extraction.",
    needsPdfTextHint: "PDF extraction is paused until a text-layer extractor is configured; OCR is not used by default.",
    knowledgeBase: "Knowledge base", researchLibrary: "Research library", newResearch: "New research",
    researchFlowNote: "Approved is the current published state: only approved research is projected into search and the knowledge graph.",
    "researchTab.all": "All documents", "researchTab.review": "Needs review", "researchTab.published": "Approved / published", "researchTab.failed": "Rejected",
    noResearchInView: "No research items in this view.", openOriginalSource: "Open original source",
    library: "Library", noSummary: "No summary yet", title: "Title", summary: "Summary",
    markdownContent: "Markdown content", tagsComma: "Tags (comma separated)", saving: "Saving…",
    saveVersion: "Save new version", createDraft: "Create draft", unableSave: "Unable to save",
    content: "Content", edit: "Edit", notFound: "Research item not found.", submitReview: "Submit for review",
    archive: "Archive", aiSuggestions: "AI suggestions", aiSeparate: "Suggestions remain separate until accepted.",
    enriching: "Enriching…", summarizeExtract: "Summarize & extract concepts", acceptSummaryTags: "Accept summary & tags",
    discovery: "Discovery", searchResearch: "Search research", searchApproved: "Search approved research…",
    allResearchTypes: "All types", internalResearch: "Internal research", reference: "Reference", deepResearch: "Deep research report",
    searchAction: "Search", searchFailed: "Search failed", results: "result(s)",
    rssCollector: "RSS collector", addSource: "Add source", name: "Name", feedUrl: "Feed URL", addRss: "Add RSS source",
    sources: "Sources", runNow: "Run now", runningFeed: "Running feed…", discovered: "discovered", reviewQueue: "Review queue", noReview: "No items need review.",
    graphCoverage: "Graph coverage", gapWorkspace: "Knowledge gap workspace", gapIntro: "Detect under-covered concepts, assign research, and keep AI-created reports behind human approval.",
    gapCardDescription: "Find topics with too few sources, claims without enough evidence, and domains that need deeper research.",
    scanCoverage: "Scan graph coverage", scanning: "Scanning…", defaultAssignee: "Default assignee", trackedGaps: "tracked gap(s)",
    priority: "Priority", concept: "Concept", approvedCoverage: "Approved coverage", owner: "Owner", unassigned: "unassigned", assign: "Assign", createDeepDraft: "Create deep-research draft", dismiss: "Dismiss", noGaps: "No gaps tracked yet. Scan graph coverage to begin.",
    governedDatasets: "Governed datasets", trainingHub: "Training Data Hub", captureDemo: "Capture expert demonstration", instruction: "Instruction", expectedResponse: "Expected response", createCandidate: "Create candidate", clearAccept: "Clear checks & accept", datasetVersions: "Dataset versions", newDataset: "New dataset", examples: "example(s)", buildAccepted: "Build accepted", exportJsonl: "Export JSONL",
    "status.draft": "draft", "status.in-review": "in review", "status.approved": "approved", "status.archived": "archived", "status.rejected": "rejected", "status.candidate": "candidate", "status.built": "built", "status.dismissed": "dismissed", "status.filled": "filled", "status.assigned": "assigned", "status.prioritized": "prioritized", "status.snoozed": "snoozed", "status.deep-research-requested": "research requested",
  },
  vi: {
    submissionQueued: "Liên kết đã vào hàng chờ xử lý. Trạng thái sẽ tự động cập nhật.", existingSubmission: "URL này đã tồn tại",
    "status.queued": "đang chờ", "status.extracting": "đang xử lý", "status.retrying": "chờ thử lại", "status.needs-review": "cần duyệt", "status.needs-transcript": "cần transcript", "status.needs-text-layer": "cần text layer PDF", "status.dead-letter": "cần can thiệp", "status.failed": "thất bại", "status.duplicate": "trùng lặp",
    dashboard: "Tổng quan", research: "Nghiên cứu", search: "Tìm kiếm", graph: "Đồ thị tri thức",
    gaps: "Khoảng trống tri thức", intake: "Nhập liên kết", collector: "Bộ thu thập", training: "Dữ liệu huấn luyện",
    workspace: "Không gian nghiên cứu thông minh", headline: "Biến các liên kết rời rạc thành tri thức có kết nối.",
    intro: "Thu thập, kiểm duyệt, làm giàu và lập bản đồ nghiên cứu đáng tin cậy về AI agent cho doanh nghiệp.",
    openIntake: "Gửi liên kết", exploreGraph: "Khám phá đồ thị", systemFlow: "Luồng hệ thống",
    flowText: "Liên kết → trích xuất → phân loại → duyệt → xuất bản → đồ thị", language: "Ngôn ngữ",
    graphTitle: "Đồ thị tri thức tương tác", graphIntro: "Khám phá các thực thể có kiểu và bằng chứng kết nối chúng.",
    allTypes: "Tất cả loại nút", findNode: "Tìm nút…", fit: "Vừa khung", relayout: "Sắp xếp lại",
    selectNode: "Chọn một nút để xem các kết nối.", connections: "kết nối trực tiếp",
    nodes: "nút", edges: "cạnh", clusters: "cụm", legend: "Chú giải", loading: "Đang tải…",
    graphProjection: "Projection đồ thị", nodeInspector: "Kiểm tra nút", submissionFailed: "Gửi liên kết thất bại",
    reset: "Đặt lại", graphProvider: "Nguồn dữ liệu đồ thị", graphTruncated: "Kết quả đã được giới hạn để đồ thị luôn phản hồi tốt.",
    graphExpandFailed: "Không thể mở rộng nút này.", graphLoadFailed: "Không thể tải đồ thị tri thức",
    graphEmpty: "Không có tri thức đã xuất bản phù hợp", graphEmptyHint: "Hãy xuất bản nghiên cứu đã duyệt hoặc đặt lại bộ lọc.",
    topics: "Chủ đề", noTopics: "Không có chủ đề trong chế độ xem này.", filters: "Bộ lọc", nodeTypes: "Loại nút", timeRange: "Khoảng thời gian",
    evidence: "Bằng chứng", relatedEvidence: "Tài liệu & bằng chứng liên quan",
    intakeTitle: "Nhập và duyệt liên kết", intakeIntro: "API ổn định cho thao tác thủ công và Discord bot trong tương lai.",
    url: "URL công khai", provider: "Nhà cung cấp AI", submit: "Trích xuất & phân loại", inbox: "Hộp thư liên kết",
    source: "Nguồn", confidence: "Độ tin cậy", relevance: "Mức liên quan", approve: "Duyệt & xuất bản",
    reject: "Từ chối", retry: "Thử lại", openResearch: "Mở nghiên cứu", noLinks: "Chưa có liên kết nào.",
    configured: "đã cấu hình", unavailable: "cần API key", status: "Trạng thái",
    needsTranscriptHint: "Thu thập Facebook Reel đã tạm dừng an toàn. Cần bổ sung transcript kèm timestamp trước khi AI trích xuất.",
    needsPdfTextHint: "Trích xuất PDF đang chờ cấu hình text-layer extractor; hệ thống không dùng OCR mặc định.",
    knowledgeBase: "Kho tri thức", researchLibrary: "Thư viện nghiên cứu", newResearch: "Nghiên cứu mới",
    researchFlowNote: "Đã duyệt là trạng thái xuất bản hiện tại: chỉ research đã duyệt được đưa vào tìm kiếm và đồ thị tri thức.",
    "researchTab.all": "Tất cả tài liệu", "researchTab.review": "Chờ kiểm duyệt", "researchTab.published": "Đã duyệt / xuất bản", "researchTab.failed": "Đã từ chối",
    noResearchInView: "Không có tài liệu trong chế độ xem này.", openOriginalSource: "Mở nguồn gốc",
    library: "Thư viện", noSummary: "Chưa có tóm tắt", title: "Tiêu đề", summary: "Tóm tắt",
    markdownContent: "Nội dung Markdown", tagsComma: "Thẻ (ngăn cách bằng dấu phẩy)", saving: "Đang lưu…",
    saveVersion: "Lưu phiên bản mới", createDraft: "Tạo bản nháp", unableSave: "Không thể lưu",
    content: "Nội dung", edit: "Chỉnh sửa", notFound: "Không tìm thấy mục nghiên cứu.", submitReview: "Gửi duyệt",
    archive: "Lưu trữ", aiSuggestions: "Đề xuất AI", aiSeparate: "Đề xuất được tách riêng cho đến khi được chấp nhận.",
    enriching: "Đang làm giàu…", summarizeExtract: "Tóm tắt & trích xuất khái niệm", acceptSummaryTags: "Chấp nhận tóm tắt & thẻ",
    discovery: "Khám phá", searchResearch: "Tìm kiếm nghiên cứu", searchApproved: "Tìm nghiên cứu đã duyệt…",
    allResearchTypes: "Tất cả loại", internalResearch: "Nghiên cứu nội bộ", reference: "Tài liệu tham khảo", deepResearch: "Báo cáo nghiên cứu sâu",
    searchAction: "Tìm kiếm", searchFailed: "Tìm kiếm thất bại", results: "kết quả",
    rssCollector: "Bộ thu thập RSS", addSource: "Thêm nguồn", name: "Tên", feedUrl: "URL RSS", addRss: "Thêm nguồn RSS",
    sources: "Nguồn", runNow: "Chạy ngay", runningFeed: "Đang chạy feed…", discovered: "đã phát hiện", reviewQueue: "Hàng chờ duyệt", noReview: "Không có mục cần duyệt.",
    graphCoverage: "Độ phủ đồ thị", gapWorkspace: "Không gian khoảng trống tri thức", gapIntro: "Phát hiện các khái niệm thiếu độ phủ, phân công nghiên cứu và giữ báo cáo AI sau bước duyệt của con người.",
    gapCardDescription: "Phát hiện chủ đề còn thiếu nguồn, claim chưa đủ bằng chứng và các lĩnh vực chưa được nghiên cứu sâu.",
    scanCoverage: "Quét độ phủ đồ thị", scanning: "Đang quét…", defaultAssignee: "Người phụ trách mặc định", trackedGaps: "khoảng trống đang theo dõi",
    priority: "Ưu tiên", concept: "Khái niệm", approvedCoverage: "Độ phủ đã duyệt", owner: "Phụ trách", unassigned: "chưa phân công", assign: "Phân công", createDeepDraft: "Tạo bản nháp nghiên cứu sâu", dismiss: "Bỏ qua", noGaps: "Chưa có khoảng trống nào. Hãy quét độ phủ đồ thị để bắt đầu.",
    governedDatasets: "Dataset có quản trị", trainingHub: "Trung tâm dữ liệu huấn luyện", captureDemo: "Ghi nhận minh hoạ chuyên gia", instruction: "Yêu cầu", expectedResponse: "Phản hồi kỳ vọng", createCandidate: "Tạo ứng viên", clearAccept: "Xác nhận kiểm tra & chấp nhận", datasetVersions: "Phiên bản dataset", newDataset: "Dataset mới", examples: "ví dụ", buildAccepted: "Build mục đã chấp nhận", exportJsonl: "Xuất JSONL",
    "status.draft": "bản nháp", "status.in-review": "đang duyệt", "status.approved": "đã duyệt", "status.archived": "đã lưu trữ", "status.rejected": "đã từ chối", "status.candidate": "ứng viên", "status.built": "đã build", "status.dismissed": "đã bỏ qua", "status.filled": "đã lấp", "status.assigned": "đã phân công", "status.prioritized": "đã ưu tiên", "status.snoozed": "đã hoãn", "status.deep-research-requested": "đã yêu cầu nghiên cứu",
  },
};

const LocaleContext = createContext({
  locale: "en" as Locale,
  setLocale: (locale: Locale) => { void locale; },
  t: (key: string) => key,
});

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");
  useEffect(() => {
    const saved = localStorage.getItem("research-locale");
    if (saved === "en" || saved === "vi") setLocale(saved);
  }, []);
  useEffect(() => {
    localStorage.setItem("research-locale", locale);
    document.documentElement.lang = locale;
  }, [locale]);
  const value = useMemo(() => ({ locale, setLocale, t: (key: string) => messages[locale][key] ?? key }), [locale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useI18n() { return useContext(LocaleContext); }
