# Báo cáo trạng thái dự án Business AI Agents Research System

**Ngày cập nhật:** 2026-07-25  
**Người yêu cầu/nghiệm thu:** Linh  
**Phạm vi báo cáo:** Graph Intelligence v2, document graph, paper-fit, chatbot, Harness và runtime local.

## 1. Kết luận điều hành

Phần kỹ thuật của bốn trong năm yêu cầu Graph Intelligence cốt lõi đã hoàn thành. Yêu cầu chatbot
đã hoạt động bằng DeepSeek, nhưng OpenAI/ChatGPT thật chưa chạy thành công do credential hiện tại
bị upstream từ chối với HTTP 401.

AI hiện có thể đọc graph, phân tích tài liệu, xác định vị trí phù hợp và tự tạo đề xuất thay đổi.
AI không được ghi thẳng vào canonical knowledge graph: đề xuất phải qua Graph Change Set, validation
và phê duyệt của người dùng trước khi apply. Đây là ranh giới quản trị đã được chấp nhận, không phải
lỗi kỹ thuật.

Project đang chạy ổn định trong môi trường local. Chưa thể tuyên bố hoàn thành toàn bộ dự án vì còn
product-owner walkthrough, quyết định rollout, OpenAI switchback tùy chọn và các hạng mục production
deployment.

## 2. Đối chiếu từng yêu cầu

| Yêu cầu | Trạng thái | Đã làm được | Chưa làm được hoặc giới hạn |
| --- | --- | --- | --- |
| Setup Harness, đọc AI_LOGS và đặt goal | Đã setup; goal chưa hoàn tất | Repository Harness `v0.1.17`, intake, story, trace, audit và AI_LOGS đang hoạt động. Harness audit hiện `0/100`. | Goal tổng vẫn ở trạng thái `blocked`; story nghiệm thu `US-GV2-ACCEPT` còn `in_progress` vì cần product owner xác nhận. |
| Có framework để AI đánh giá paper phù hợp với hệ thống | Hoàn thành kỹ thuật | Có rubric phiên bản hóa, hard gates, score, routing, matched pillars, candidate parents, limitations và explanation. | Chưa có xác nhận của product owner rằng cách chấm và giải thích phù hợp nghiệp vụ thực tế. |
| Upload tài liệu lên thì có graph riêng | Hoàn thành kỹ thuật | Mỗi PDF, DOCX, TXT, Markdown, LaTeX, reStructuredText, AsciiDoc hoặc HTML hợp lệ tạo một Document Graph Workspace riêng với nodes, edges, evidence, provenance và trạng thái xử lý. Định dạng nguồn text có Raw/Preview/Song song. | ODT/RTF chưa hỗ trợ chính thức. OCR là tùy chọn và đang tắt mặc định. |
| Hiển thị node cha và node con | Hoàn thành | Có hierarchy view, relationship view, breadcrumb, lazy child loading, parent placement và cycle validation. | Không có blocker kỹ thuật hiện tại. |
| Trong bảng có danh sách node; bấm bảng mới hiện node | Hoàn thành | Ban đầu hiện root và 11 bảng. Bấm một bảng thì chính bảng đó mở thành container chứa node con; các bảng khác vẫn còn. Bấm lại header để thu gọn. | Interaction external-branch cũ đã bị thay thế hoàn toàn. |
| Graph chính có các phần để AI ghép node | Hoàn thành kỹ thuật | Có root `Business AI Agents`, 11 pillar ổn định, placement candidate, alias/duplicate detection và change review. | Taxonomy cấp sâu vẫn tiếp tục được mở rộng theo tài liệu thực tế. |
| AI tự tìm hiểu và ghép node vào hệ thống | Hoàn thành có kiểm soát | AI phân tích tài liệu/context, tìm parent phù hợp, kiểm tra evidence và tạo Graph Change Set để review/apply. | Chưa có autonomous web research liên tục. AI không tự publish hoặc tự merge thẳng vào canonical graph. |
| Chatbot brainstorm với knowledge graph | Hoạt động bằng DeepSeek | Có `/chat`, scoped graph context, read/propose tools, session history và proposal/change-set linking. DeepSeek đã tạo một proposal thật hợp lệ. | Prompt quá rộng có thể dừng ở `CHAT_TOOL_LOOP_LIMIT` và cần chia nhỏ yêu cầu. |
| Dùng ChatGPT/OpenAI | Có adapter, chưa chạy live | OpenAI Responses adapter, strict tools, `store: false`, redaction và provider switch đã có. | Credential OpenAI hiện tại trả HTTP 401 nên chưa có turn OpenAI thật thành công. |
| Tạm dùng DeepSeek và đổi sang OpenAI sau | Hoàn thành | DeepSeek `deepseek-v4-pro` đang là provider mặc định. Chuyển sang OpenAI là thay đổi cấu hình, không phải sửa workflow hoặc database. | Cần OpenAI key hợp lệ và chạy lại provider preflight. |
| Chạy project | Hoàn thành local | Frontend, API, worker và PostgreSQL đang chạy; graph, documents và chat trả HTTP 200. | Chưa phải production internet-facing deployment. |

## 3. Những phần đã hoàn thành

### 3.1. Paper-fit framework

AI đánh giá tài liệu theo bảy chiều:

1. Mức phù hợp với hệ thống.
2. Khả năng áp dụng kinh doanh.
3. Chất lượng bằng chứng.
4. Tính mới.
5. Giá trị triển khai.
6. Khả năng lấp khoảng trống kiến thức.
7. Độ mới của thông tin.

Các routing band hiện tại:

| Điểm | Quyết định |
| ---: | --- |
| Dưới 40 | `not_relevant` |
| 40–59 | `watch` |
| 60–79 | `draft_graph` |
| Từ 80 | `priority_review` |

Hard-gate failure không nhận một điểm fit gây hiểu nhầm. Kết quả còn trả về matched pillars,
candidate parents, contribution types, overlaps, gaps, limitations, explanation và confidence.

Gold set 30 paper đạt `1.00` trên bộ fixture đối với routing, top-three placement và near-duplicate
detection. Đây là bằng chứng regression trên tập kiểm thử phiên bản hóa, không phải cam kết chất
lượng cho mọi paper ngoài thực tế.

### 3.2. Document graph riêng

Luồng đã triển khai:

```text
Upload
  → Bounded extraction
  → Paper-fit evaluation
  → Isolated Document Graph
  → Ontology mapping proposal
  → Graph Change Set
  → Human review
  → Canonical knowledge graph
```

Mỗi tài liệu giữ graph riêng cho đến khi change set được duyệt. Workspace chứa:

- processing status và typed failure/retry;
- node, edge và parent-child containment;
- source evidence và evidence location;
- AI provider, model và prompt version;
- confidence, limitation và provenance;
- duplicate/content-hash protection.

### 3.3. Canonical Business AI Agents graph

Graph chính có một root và 11 pillar:

1. Business Problems & Outcomes.
2. Business Context.
3. Agent System Architecture.
4. Agent Capabilities & Workflows.
5. Business Methods & Decision Intelligence.
6. Data, Knowledge & Memory.
7. Tools, Functions & Integrations.
8. Outputs, Actions & Feedback.
9. Evaluation, Risk & Governance.
10. Engineering & Operations.
11. Research & Evidence.

Runtime hiện báo canonical graph hợp lệ với 45 nodes, 32 edges và không có cycle, dangling endpoint
hoặc invariant error.

### 3.4. Compound/folding board graph

Hierarchy chính đã được sửa theo interaction yêu cầu:

- trạng thái đầu chỉ hiển thị system root và 11 board đang đóng;
- mỗi board hiển thị số direct child;
- bấm một board sẽ lazy-load direct children;
- chính board đó mở rộng thành group container;
- mọi child card nằm trong boundary của board;
- các board còn lại vẫn hiển thị và giữ trạng thái đóng;
- board-to-child containment edges được ẩn bên trong group;
- bấm lại phần header để thu gọn.

Live proof đã mở `Data, Knowledge & Memory` thành một container ba cột chứa đủ 33 direct child
nodes.

### 3.5. Ontology mapping và graph governance

AI có thể:

- tìm canonical node và alias;
- tìm node tương tự;
- đề xuất parent/pillar;
- phát hiện duplicate candidate;
- đề xuất node, edge, alias và evidence;
- tạo Graph Change Set;
- validation evidence, confidence, endpoint, duplicate, self-loop và hierarchy cycle;
- cho phép người dùng edit, accept hoặc reject từng mutation;
- apply transactionally và idempotently;
- tạo compensating change set cho thao tác undo có quản trị.

AI không thể:

- publish trực tiếp;
- xóa canonical node bằng chat tool;
- chạy SQL tùy ý;
- bỏ qua review;
- ghi knowledge không có nguồn mà không đánh dấu `evidence_pending`.

Vì vậy, câu “AI tự add vào knowledge graph” hiện được triển khai theo nghĩa:

> AI tự tạo proposal có cấu trúc; người dùng review và apply proposal hợp lệ vào canonical graph.

### 3.6. Chatbot

Trang `/chat` hỗ trợ:

- graph, pillar, node, document, change-set và gap scope;
- bounded context retrieval;
- chat session/message history lưu local;
- graph search và node-context tools;
- draft change-set và typed mutation proposal;
- provider/tool/loop failure có mã lỗi rõ ràng;
- không gửi API key xuống browser.

DeepSeek `deepseek-v4-pro` đã được kiểm chứng bằng request thật. Một document-scoped session đã tạo
change set `5759af2f-4685-4cfa-b360-39d7981a1fa4`, trạng thái `needs_review`, có một mutation
`Cited Recommendation Review Gate` hợp lệ, có evidence và không có validation error/warning.
Mutation này chưa được approve hoặc apply.

### 3.7. Runtime và Harness

Các service local đang chạy:

| Thành phần | Địa chỉ/trạng thái |
| --- | --- |
| Frontend | `http://localhost:13000` |
| API | `http://localhost:18000` |
| PostgreSQL | Healthy trong Docker Compose |
| Worker | Running |
| Knowledge Graph | `http://localhost:13000/graph` |
| Documents | `http://localhost:13000/documents` |
| Chat | `http://localhost:13000/chat` |

Harness hiện có:

- Repository Harness `v0.1.17`;
- durable intake/story/trace database;
- cross-agent `AI_LOGS/`;
- story verification commands;
- active-matrix query;
- drift audit `0/100`.

## 4. Những phần chưa hoàn thành

### 4.1. Product-owner acceptance

Các bước sau vẫn chưa được product owner đánh dấu:

- upload một PDF/Markdown/text thật và xác nhận evaluation dễ hiểu;
- kiểm tra isolated graph, parent-child navigation và node evidence;
- tạo mapping change set, reject một mutation, approve/apply phần còn lại;
- brainstorm một concept qua scoped chat và xác nhận proposal chỉ là draft;
- review/apply grounded chat proposal và xác nhận không có mutation chưa duyệt trong graph;
- kiểm tra desktop, tablet, mobile và ngôn ngữ ưu tiên;
- xác nhận error/retry wording;
- chọn quyết định rollout.

Các lựa chọn rollout hiện vẫn để trống:

- Accepted.
- Accepted with follow-up work.
- Changes required.

Do đó story `US-GV2-ACCEPT` vẫn `in_progress` và goal tổng vẫn `blocked`.

### 4.2. OpenAI/ChatGPT runtime

Đã có:

- OpenAI Responses adapter;
- strict function tools;
- `store: false`;
- local conversation state;
- redaction;
- safe operator preflight;
- configuration-only provider switch.

Chưa có:

- OpenAI key hợp lệ;
- successful live OpenAI brainstorm;
- final OpenAI switchback proof.

Credential hiện tại bị upstream trả HTTP 401 và được application map thành
`CHAT_PROVIDER_UNAVAILABLE` mà không lộ key hoặc provider response body.

### 4.3. Autonomous research và publication

Chưa triển khai:

- AI tự động tìm kiếm Internet liên tục;
- autonomous gap research;
- automatic canonical-node merge;
- AI tự publish node/edge không cần review;
- tự động xóa hoặc thay thế accepted knowledge.

Đây là phần được defer hoặc bị giới hạn theo governance hiện tại.

### 4.4. File/source coverage

Chưa hoàn chỉnh:

- ODT/RTF và các định dạng office binary khác ngoài DOCX;
- universal OCR;
- paywall/private-source extraction;
- arbitrary Facebook Reel scraping;
- voice/realtime chat.

OCR và Browserless đã có adapter tùy chọn, nhưng không bật mặc định.

### 4.5. Production deployment

Chưa hoàn thành:

- public TLS/reverse proxy/domain deployment;
- production MinIO provisioning với TLS, encryption, lifecycle và backup;
- thực thi migration attachment cũ vào production MinIO;
- external secret manager và rotation;
- telemetry retention, alerting và dashboard vận hành;
- production HA/capacity cho Neo4j và Meilisearch;
- automatic projection synchronization.

### 4.6. Các hạng mục backlog ngoài Graph Intelligence cốt lõi

Chưa triển khai:

- scheduled collectors hoàn chỉnh;
- optional Redis transport;
- thêm collector adapters sau khi RSS được xác nhận;
- Discord bot/adapter.

Discord chỉ bắt đầu sau khi Research System completion gates và product-owner acceptance hoàn tất.

## 5. Bằng chứng kiểm thử gần nhất

| Hạng mục | Kết quả |
| --- | --- |
| Backend provider-neutral/DeepSeek suite | 168 tests pass |
| Frontend suite hiện tại | 32/32 tests pass |
| TypeScript | Pass |
| Next.js production build | Pass, 15 routes |
| Full Playwright | 30 enabled cases pass; 6 auth-only cases skip đúng cấu hình local |
| Compound-board E2E | 3/3 desktop, tablet, mobile pass |
| Runtime readiness | `ready` |
| Canonical graph | 45 nodes, 32 edges, 0 invariant error |
| Browser inspection | Không console error, page error hoặc HTTP 5xx |
| Harness audit | `0/100` |

## 6. Trạng thái tổng hợp

### Đã hoàn thành về kỹ thuật

- Paper-fit rubric và routing.
- Mỗi upload có document graph riêng.
- Parent-child hierarchy và relationship graph.
- Canonical root và 11 system pillars.
- Compound/folding board interaction.
- Ontology mapping proposal.
- Graph Change Set review/apply.
- Chatbot DeepSeek đọc graph và tạo proposal.
- OpenAI adapter và cơ chế switch provider.
- Local runtime, testing, migration, backup/restore docs và Harness.

### Đã có nhưng cần product owner nghiệm thu

- Paper-fit explanation.
- Document graph usability.
- Mapping/change-review workflow.
- DeepSeek chat wording và proposal quality.
- Responsive/bilingual usability.
- Error/retry wording.
- Rollout decision.

### Chưa hoàn thành

- OpenAI live credential và switchback proof.
- Tự động publish/merge không cần duyệt.
- Autonomous web/gap research.
- Production internet-facing deployment.
- Scheduled collectors/Redis mở rộng.
- Discord adapter.

## 7. Kết luận dùng trong báo cáo

> Graph Intelligence v2 đã hoàn thành phần kỹ thuật cốt lõi gồm paper-fit, document graph riêng,
> canonical ontology, hierarchy/compound-board UI, governed graph change workflow và chatbot
> DeepSeek. Hệ thống đang chạy ổn định tại môi trường local. Các phần chưa hoàn tất là product-owner
> acceptance, OpenAI credential switchback, autonomous publication/research và production
> deployment hardening.

## 8. Tài liệu liên quan

- [Business AI Agents Graph Intelligence Upgrade Plan](Business%20AI%20Agents%20Graph%20Intelligence%20Upgrade%20Plan.md)
- [Graph Intelligence v2 Product Acceptance Checklist](Graph%20Intelligence%20v2%20Product%20Acceptance%20Checklist.md)
- [Graph Intelligence v2 Operations Runbook](Graph%20Intelligence%20v2%20Operations%20Runbook.md)
- [AI handoff log](../AI_LOGS/HANDOFF.md)
- [AI task board](../AI_LOGS/TASKS.md)
