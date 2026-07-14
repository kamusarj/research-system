# Research System Implementation Plan

> Kế hoạch triển khai hệ thống Research System dựa trên:
>
> - `Docs/Research System Brainstorm.md`
> - `Docs/Research System Architecture Design.md`
>
> **Trạng thái:** Phase 0-7 complete; Phase 8 in progress  
> **Mục tiêu hiện tại:** Gap Intelligence MVP sau khi Research KB/search/graph đã được kiểm chứng  
> **Phạm vi ưu tiên:** Local-first, human-approved deep research
>
> Cập nhật 2026-07-13: implementation hiện nằm trong `apps/api` và `apps/web`. Phase 8 đã có
> graph low-coverage detector, gap workspace, assign/prioritize/dismiss/snooze, tạo deep-research
> draft và human approval gate. Trend/failed-search signals và weekly digest vẫn để bước sau.
>
> Kế hoạch hoàn thiện hệ thống trước Discord integration được chốt tại
> `Docs/Research System Completion Plan.md`.

---

## 1. Mục tiêu triển khai

Triển khai hệ thống Research System theo hướng từng bước, bắt đầu từ một MVP dùng được local để team quản lý research về **AI Agents for Business**.

MVP cần giải quyết trước:

- Lưu trữ research tập trung.
- Tạo/sửa/duyệt research bằng Markdown.
- Tìm kiếm full-text và semantic search cơ bản.
- Trực quan hóa Knowledge Graph cơ bản.
- AI hỗ trợ summarize, tag, extract concepts.
- Có nền móng cho auto-collector và training data hub, nhưng chưa cần full automation ngay.

Không làm ngay trong MVP:

- Multi-source crawler phức tạp.
- Deep research agent tự động hoàn chỉnh.
- Fine-tune runner/model training pipeline.
- Production SSO/Keycloak.
- Kubernetes hoặc cloud deployment.

---

## 2. Chiến lược triển khai

### 2.1. Cách tiếp cận

Triển khai theo hướng **local-first, modular, upgradeable**:

1. Dựng bản local chạy được nhanh.
2. Giữ API và data model gần với architecture cuối.
3. Tách rõ core domain, worker pipeline và projection layer.
4. Cho phép thay lightweight component bằng full component sau này.

### 2.2. Kiến trúc mục tiêu

Kiến trúc cuối vẫn theo tài liệu architecture:

- Frontend: Next.js.
- Backend: FastAPI.
- Primary DB: PostgreSQL + pgvector.
- Graph: Neo4j.
- Search: Meilisearch.
- Queue/cache: Redis.
- File storage: MinIO.
- Local LLM: Ollama.
- Worker: Celery/RQ hoặc equivalent.

### 2.3. Kiến trúc MVP local

Để tránh overbuild, MVP local có thể bắt đầu bằng:

- Backend FastAPI.
- SQLite hoặc PostgreSQL local.
- Static/Next.js frontend tùy thời gian.
- Search đơn giản trước, Meilisearch ở phase sau.
- Graph API projection đơn giản trước, Neo4j ở phase sau.
- Mock/Ollama adapter cho AI enrichment.

Quy tắc: dù dùng lightweight backend ban đầu, API paths và schema phải thiết kế theo `/api/v1` để không phá frontend khi nâng cấp.

---

## 3. Phạm vi chức năng theo phase

## Phase 0 - Product & Technical Spec

Mục tiêu: biến brainstorm thành bộ spec đủ rõ để implement.

Deliverables:

- Product spec cho MVP.
- API contract.
- Database schema v1.
- UI flow/wireframe thực tế hơn.
- Local deployment guide.
- Danh sách acceptance criteria.
- AI handoff log format để nhiều AI agents có thể tiếp quản công việc luân phiên.

Nội dung cần chốt:

- Research item lifecycle.
- Required metadata.
- Role permissions.
- Search/filter behavior.
- Graph node/edge types trong MVP.
- AI fields nào auto-generated, fields nào human-editable.
- Quy ước ghi log khi đổi agent hoặc hết quota.

Acceptance:

- Một engineer đọc docs có thể bắt đầu implement mà không cần hỏi lại các quyết định lớn.
- Một AI agent mới có thể đọc handoff log trong 5 phút và biết ngay trạng thái hiện tại, việc đang làm, việc không được động vào.

---

## Phase 1 - Local Foundation

Mục tiêu: tạo skeleton app chạy local.

Backend:

- FastAPI app.
- `/api/v1/health`.
- Config bằng `.env`.
- Database connection.
- Migration mechanism.
- Basic error format.
- CORS cho frontend local.

Frontend:

- App shell.
- Sidebar/navigation.
- Dashboard placeholder.
- API client.

Infrastructure:

- Docker Compose local.
- Services tối thiểu: api, frontend, database.
- Optional services sau: redis, meilisearch, neo4j, minio, ollama.

Acceptance:

- Chạy được app local bằng một lệnh.
- Health check pass.
- Frontend gọi được backend.

---

## Phase 2 - Research Knowledge Base Core

Mục tiêu: quản lý research item thủ công.

Backend features:

- Create research item.
- List research items với filter.
- Get detail.
- Update.
- Archive/delete mềm.
- Submit review.
- Approve.
- Version history.
- Comments basic.
- Tags.
- Relations thủ công.

Research item fields:

- `id`
- `display_id`
- `title`
- `type`
- `status`
- `collection_method`
- `summary`
- `content`
- `source_url`
- `authors`
- `tags`
- `created_at`
- `updated_at`
- `approved_at`
- `metadata`

Frontend features:

- Research list.
- Research detail.
- Markdown editor.
- Metadata panel.
- Status badge.
- Tag editor.
- Relations section.

Acceptance:

- User tạo research draft.
- User submit review.
- Admin/researcher approve.
- Approved item hiển thị trong library.
- Edit tạo version snapshot.

---

## Phase 3 - Search & Discovery

Mục tiêu: tìm kiếm research hiệu quả.

Backend:

- Full-text search.
- Filter theo status, type, tag, collection method, date.
- Related research API dựa trên tag/relation ban đầu.
- Semantic search nếu pgvector/embedding đã sẵn sàng.

Frontend:

- Search page.
- Search bar global.
- Filters.
- Result cards.
- Related research trên detail page.

Implementation path:

1. Bắt đầu bằng database full-text hoặc simple search.
2. Thêm Meilisearch projection khi core ổn.
3. Thêm embedding chunks và semantic search sau.

Acceptance:

- Search title/content/tags hoạt động.
- Filter không làm mất pagination.
- Approved item mới có thể search sau khi lưu.

---

## Phase 4 - Knowledge Graph MVP

Mục tiêu: có graph visualization cơ bản.

Node types MVP:

- ResearchItem.
- Concept.
- Technology.
- Person.
- BusinessDomain.
- CollectorSource.

Edge types MVP:

- RESEARCHES.
- USES_TECH.
- AUTHORED_BY.
- APPLIES_TO.
- REFERENCES.
- EXTENDS.
- SUPPORTS.
- CONTRADICTS.

Backend:

- Build graph projection từ research items, tags, relations.
- `/api/v1/graph`.
- `/api/v1/graph/node/{id}`.
- `/api/v1/graph/ego/{id}`.
- `/api/v1/graph/path`.

Frontend:

- Graph viewer.
- Node filters.
- Click node để xem detail.
- Ego graph.
- Legend.

Implementation path:

1. Graph projection in-memory/database query trước.
2. Sau đó sync sang Neo4j.

Acceptance:

- Approved research xuất hiện trong graph.
- Tags/concepts thành node.
- Manual relations thành edge.
- Click node mở detail panel.

---

## Phase 5 - AI Enrichment

Mục tiêu: AI hỗ trợ xử lý research.

Features:

- Summarize content.
- Extract concepts.
- Suggest tags.
- Suggest relations.
- Generate embedding.

Backend:

- `LLMProvider` interface.
- Ollama provider.
- Mock provider cho local/test.
- AI provenance table/metadata.
- Background job hoặc sync job tùy MVP.

AI provenance cần lưu:

- `model_name`
- `model_version`
- `prompt_version`
- `input_hash`
- `output_json`
- `confidence`
- `created_at`

Frontend:

- Button `Summarize`.
- Button `Extract Concepts`.
- AI suggestion panel.
- Accept/reject/edit suggested tags and relations.

Acceptance:

- AI-generated field phân biệt rõ với human field.
- Human edit không bị AI ghi đè tự động.
- Có thể re-run enrichment.

---

## Phase 6 - Auto-Collector MVP

Mục tiêu: ingest tự động từ một nguồn đơn giản.

Source đầu tiên đề xuất:

- RSS feeds.

Lý do:

- Dễ chạy local.
- Ít phụ thuộc API key.
- Phù hợp blog/docs/news về AI agents.

Collector lifecycle:

1. Discover.
2. Fetch.
3. Normalize.
4. Deduplicate.
5. Evaluate.
6. Auto-approve/review/reject.
7. Ingest.
8. Enrich.
9. Index/search/graph sync.

Backend:

- Collector sources CRUD.
- Manual run source.
- Run history.
- Review queue.
- Approve/reject/edit-and-approve.

Frontend:

- Collector Manager.
- Source health.
- Review queue.
- Score breakdown.

Default threshold:

- Auto-approve: score >= 80.
- Review: score 50-79.
- Reject: score < 50.

Acceptance:

- Add RSS source.
- Run collector manually.
- Items discovered and evaluated.
- Approved item becomes research item.

---

## Phase 7 - Training Data Hub Foundation

Mục tiêu: đặt nền móng thu thập dữ liệu fine-tune, chưa train model.

Entities:

- TrainingEvent.
- TrainingExample.
- PreferencePair.
- TrainingDataset.
- ModelEvalRun.

Backend:

- Ingest raw training event.
- Convert event to candidate example.
- Accept/reject/eval-only example.
- Dataset builder.
- Export JSONL.

Frontend:

- Training Data Hub page.
- Example review queue.
- Dataset versions.
- Export manager.

Governance:

- PII status required.
- Policy status required.
- Provenance required.
- Holdout split không dùng để synthetic generation.

Acceptance:

- Có thể ingest một agent trace.
- Có thể tạo training example.
- Có thể approve example.
- Có thể export JSONL dataset.

---

## Phase 8 - Gap Intelligence & Deep Research

Mục tiêu: chỉ triển khai sau khi KB/search/graph đã ổn.

Features:

- Graph coverage metrics.
- Knowledge gap detection.
- Gap workspace.
- Assign researcher.
- Request AI deep research.
- Human approval before publish.
- Weekly digest.

Acceptance:

- System gợi ý gaps dựa trên coverage.
- Human có thể dismiss/assign/request deep research.
- Deep research report vào lifecycle review trước khi approved.

---

## 4. Data Model v1

### Core tables

- `users`
- `research_items`
- `research_versions`
- `tags`
- `research_tags`
- `research_relations`
- `attachments`
- `comments`
- `audit_events`
- `outbox_events`

### Search/AI tables

- `embedding_chunks`
- `ai_outputs`

### Collector tables

- `collector_sources`
- `collector_runs`
- `discovered_items`
- `evaluations`

### Training data tables

- `training_events`
- `training_examples`
- `training_datasets`
- `training_dataset_examples`
- `preference_pairs`
- `model_eval_runs`

---

## 5. API Surface v1

### Research

```text
GET    /api/v1/research
POST   /api/v1/research
GET    /api/v1/research/{id}
PUT    /api/v1/research/{id}
DELETE /api/v1/research/{id}
POST   /api/v1/research/{id}/submit-review
POST   /api/v1/research/{id}/approve
POST   /api/v1/research/{id}/archive
GET    /api/v1/research/{id}/versions
GET    /api/v1/research/{id}/relations
POST   /api/v1/research/{id}/relations
POST   /api/v1/research/{id}/attachments
```

### Search

```text
GET    /api/v1/search?q=
POST   /api/v1/search/semantic
GET    /api/v1/search/suggest?q=
GET    /api/v1/research/{id}/related
```

### Graph

```text
GET    /api/v1/graph
GET    /api/v1/graph/node/{id}
GET    /api/v1/graph/ego/{id}
GET    /api/v1/graph/path?from=&to=
GET    /api/v1/graph/stats
POST   /api/v1/graph/rebuild
```

### AI

```text
POST   /api/v1/ai/summarize
POST   /api/v1/ai/extract-concepts
POST   /api/v1/ai/suggest-relations
POST   /api/v1/ai/enrich/{research_id}
```

### Collector

```text
GET    /api/v1/collector/sources
POST   /api/v1/collector/sources
PUT    /api/v1/collector/sources/{id}
POST   /api/v1/collector/sources/{id}/run
GET    /api/v1/collector/runs
GET    /api/v1/collector/review-queue
POST   /api/v1/collector/review-queue/{id}/approve
POST   /api/v1/collector/review-queue/{id}/reject
```

### Training Data

```text
POST   /api/v1/training/events
GET    /api/v1/training/events
POST   /api/v1/training/events/{id}/convert
GET    /api/v1/training/examples
PUT    /api/v1/training/examples/{id}
POST   /api/v1/training/examples/{id}/accept
POST   /api/v1/training/examples/{id}/reject
POST   /api/v1/training/examples/{id}/eval-only
POST   /api/v1/training/datasets
POST   /api/v1/training/datasets/{id}/build
POST   /api/v1/training/datasets/{id}/export
```

---

## 6. Frontend Screens

### MVP screens

- Dashboard.
- Research list.
- Research detail.
- Research editor.
- Search page.
- Graph viewer.
- Settings/basic admin.

### Phase 2+ screens

- Collector Manager.
- Review Queue.
- Gap Workspace.
- Training Data Hub.
- Dataset Builder.
- Model Eval Dashboard.

---

## 7. Testing Plan

### Unit tests

- Research status transitions.
- Version snapshot creation.
- Tag normalization.
- Relation validation.
- Search query parser.
- Collector dedup.
- Dataset split validation.

### API tests

- CRUD research.
- Submit/approve/archive.
- Search/filter.
- Graph endpoint shape.
- AI enrichment with mock provider.
- Collector approve/reject.
- Training example accept/reject/export.

### Integration tests

- Postgres/SQLite write → search projection.
- Research write → graph projection.
- Attachment upload metadata.
- Outbox event retry/idempotency.
- Collector run → discovered item → ingested research item.

### E2E tests

- Create draft → approve → appears in search.
- Create relation → appears in graph.
- Run AI summarize → accept summary.
- Collector RSS item → approve → appears in library.
- Training event → candidate example → accept → export JSONL.

---

## 8. AI Handoff Log Design

Mục tiêu: tạo một cơ chế log chuẩn để khi hết quota hoặc đổi AI agent, agent mới có thể tiếp quản nhanh mà không cần đọc lại toàn bộ lịch sử chat.

### 8.1. Nguyên tắc

- Log phải nằm trong repo để mọi agent đều đọc được.
- Log phải ngắn, có cấu trúc, cập nhật sau mỗi phiên làm việc lớn.
- Log không thay thế docs chính; nó là trạng thái vận hành hiện tại.
- Log phải ghi rõ việc đã làm, việc đang dở, quyết định đã chốt, và vùng không được sửa.
- Không lưu secret, token, credential, customer PII trong log.

### 8.2. File đề xuất

Tạo thư mục:

```text
AI_LOGS/
├── HANDOFF.md                  # trạng thái mới nhất, agent nào cũng đọc đầu tiên
├── DECISIONS.md                # quyết định kỹ thuật/product đã chốt
├── TASKS.md                    # backlog và trạng thái task
├── SESSIONS/
│   └── 2026-07-09-session-001.md
└── TEMPLATES/
    ├── handoff-template.md
    └── session-template.md
```

Quy ước đọc:

1. Agent mới đọc `AI_LOGS/HANDOFF.md`.
2. Nếu cần lý do quyết định, đọc `AI_LOGS/DECISIONS.md`.
3. Nếu cần lịch sử chi tiết, đọc session gần nhất trong `AI_LOGS/SESSIONS/`.
4. Sau khi làm xong, agent cập nhật `HANDOFF.md` và tạo session log mới.

### 8.3. HANDOFF.md format

```markdown
# AI Handoff Log

## Current Goal
- Goal hiện tại:
- Người yêu cầu:
- Trạng thái: planning / implementing / blocked / ready-for-review

## Current State
- Repo hiện có:
- Files quan trọng:
- App chạy bằng:
- Tests chạy bằng:

## Completed
- [x] Việc đã hoàn thành

## In Progress
- [ ] Việc đang làm dở
- File liên quan:
- Branch/commit nếu có:

## Next Best Actions
1. Việc nên làm tiếp theo
2. Việc tiếp theo sau đó

## Decisions Locked
- Quyết định đã chốt, không tự đổi nếu không hỏi user.

## Do Not Touch
- Files/areas không được sửa.
- User changes chưa được revert.

## Known Issues
- Bug/rủi ro/blocker hiện tại.

## Verification
- Lệnh đã chạy:
- Kết quả:
- Lệnh chưa chạy được:
```

### 8.4. Session log format

Mỗi agent khi kết thúc một lượt làm việc đáng kể tạo một file trong `AI_LOGS/SESSIONS/`.

Tên file:

```text
YYYY-MM-DD-HHMM-agent-short-summary.md
```

Template:

```markdown
# Session Log

## Context
- User request:
- Agent:
- Date/time:

## Work Done
- Files changed:
- Behavior changed:
- Commands run:

## Reasoning / Decisions
- Decision:
- Reason:
- Alternatives considered:

## Verification
- Tests/checks:
- Result:

## Next Agent Notes
- Continue from:
- Watch out for:
- Suggested next command:
```

### 8.5. TASKS.md format

`TASKS.md` dùng để agent mới không phải tự suy luận backlog.

```markdown
# Task Board

## Now
- [ ] Task ưu tiên cao nhất

## Next
- [ ] Task tiếp theo

## Later
- [ ] Task sau MVP

## Blocked
- [ ] Task bị block
  - Blocker:
  - Cần user quyết định:

## Done
- [x] Task đã xong
```

### 8.6. DECISIONS.md format

`DECISIONS.md` là lightweight ADR log.

```markdown
# Decisions

## DEC-001 - Local-first MVP
- Date:
- Status: accepted
- Decision:
- Reason:
- Consequences:
```

### 8.7. Quy trình agent bắt đầu làm việc

Agent mới phải làm theo thứ tự:

1. Đọc `AI_LOGS/HANDOFF.md`.
2. Đọc `AI_LOGS/TASKS.md`.
3. Đọc `AI_LOGS/DECISIONS.md` nếu task có ảnh hưởng kiến trúc.
4. Kiểm tra `git status --short`.
5. Đọc files liên quan trước khi sửa.
6. Không revert thay đổi của agent/user trước nếu không được yêu cầu.
7. Làm task nhỏ nhất có thể hoàn thành.
8. Chạy verification.
9. Cập nhật handoff log.

### 8.8. Quy trình agent kết thúc phiên

Trước khi kết thúc hoặc khi gần hết quota:

1. Ghi rõ việc đã làm.
2. Ghi files đã sửa.
3. Ghi commands/tests đã chạy.
4. Ghi lỗi còn lại.
5. Ghi next best action.
6. Ghi những việc không được làm tiếp nếu chưa hỏi user.
7. Nếu có thay đổi code, ghi trạng thái git ngắn gọn.

### 8.9. Tích hợp vào Research System sau này

Khi app đã có backend, AI handoff log có thể trở thành một phần của Research System.

Entity đề xuất:

- `AgentSession`
- `AgentDecision`
- `AgentTask`
- `AgentHandoff`
- `VerificationRun`

API đề xuất:

```text
GET    /api/v1/agent-handoff/current
POST   /api/v1/agent-handoff/sessions
POST   /api/v1/agent-handoff/decisions
GET    /api/v1/agent-handoff/tasks
PUT    /api/v1/agent-handoff/tasks/{id}
```

Nhưng trong MVP hiện tại, dùng Markdown file là đủ nhanh, ít phụ thuộc và dễ dùng giữa nhiều AI agents.

### 8.10. Acceptance Criteria

- Agent mới chỉ cần đọc `AI_LOGS/HANDOFF.md` và `AI_LOGS/TASKS.md` để biết nên làm gì tiếp.
- Mỗi phiên làm việc quan trọng có session log.
- Mọi quyết định kiến trúc có entry trong `DECISIONS.md`.
- Không có secret/PII trong log.
- Log luôn nói rõ verification đã chạy hay chưa.

---

## 9. Acceptance Criteria cho MVP

MVP được xem là đạt khi:

- App chạy local bằng hướng dẫn rõ ràng.
- User tạo, sửa, duyệt research được.
- Research approved có thể search được.
- Research approved xuất hiện trong graph.
- AI enrichment chạy được bằng mock hoặc Ollama.
- Có seed data để demo.
- Có tests cho core API.
- Tài liệu setup và architecture được cập nhật theo implementation thực tế.
- Có AI handoff log để agent khác tiếp quản khi đổi agent hoặc hết quota.

---

## 10. Rủi ro và cách giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| Scope quá lớn | Bám MVP Research KB trước, collector/training làm nền tảng sau |
| Neo4j/Meilisearch làm local setup nặng | Cho phép lightweight projection trước |
| Ollama chậm hoặc thiếu model | Có mock provider và async job |
| AI output sai | Human accept/reject, lưu provenance |
| Training data lẫn PII | Bắt buộc `pii_status` và `policy_status` |
| Collector tạo junk data | Threshold + review queue + dedup |
| Đổi AI agent làm mất context | Bắt buộc cập nhật `AI_LOGS/HANDOFF.md` và session log |
| Agent mới sửa nhầm vùng đang dở | `Do Not Touch` và `In Progress` trong handoff log |

---

## 11. Thứ tự thực hiện đề xuất

1. Hoàn thiện spec files trong `Docs/`.
2. Tạo `AI_LOGS/` với handoff, decisions, tasks, session templates.
3. Scaffold backend + database.
4. Implement Research CRUD.
5. Implement frontend research library/editor.
6. Implement search.
7. Implement graph projection.
8. Implement AI enrichment mock/Ollama.
9. Implement RSS collector MVP.
10. Implement Training Data Hub foundation.
11. Polish dashboard, tests, docs.

---

## 12. Ghi chú triển khai

- Không implement full platform ngay từ đầu.
- Không để AI tự động ghi đè human-edited fields.
- Không đưa training data vào fine-tune nếu chưa có PII/policy check.
- Không dùng Neo4j làm source of truth.
- Không phụ thuộc cloud provider trong MVP.
- Mọi projection phải rebuild được từ primary database.
- Mỗi AI agent phải cập nhật handoff log trước khi dừng nếu đã thay đổi code/docs.
