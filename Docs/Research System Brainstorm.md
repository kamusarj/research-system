# Research System for AI Agents for Business

> Hệ thống tự host (self-hosted) để lưu trữ, quản lý, tự động thu thập và trực quan hóa các nghiên cứu của team về AI Agents for Business dưới dạng Knowledge Graph — với AI agents tự động đi thu thập, đánh giá và bổ sung tài liệu.

---

## 1. Mục tiêu

- **Lưu trữ tập trung** tất cả nghiên cứu của team về AI Agents for Business
- **Phân loại rõ ràng** giữa tài liệu do người thu thập và tài liệu do AI tự động thu thập
- **Tự động thu thập** tài liệu từ nhiều nguồn (arXiv, blogs, GitHub, RSS, conferences...) bằng AI agents
- **Tự động đánh giá** mức độ phù hợp, chất lượng, và độ mới của tài liệu thu thập được
- **Tự động xử lý và bổ sung** vào Knowledge Graph (summarize, extract concepts, find relations) — không cần human review từng tài liệu
- **Tự phát hiện knowledge gaps** — khi phát hiện gap lớn, AI đề xuất human research hoặc tự động deep research (human-in-the-loop chỉ can thiệp ở đây)
- **Trực quan hóa** mối quan hệ giữa các nghiên cứu, khái niệm, công nghệ qua Knowledge Graph
- **Dễ tìm kiếm, khám phá** các nghiên cứu liên quan (full-text + semantic search)
- **Thu thập dữ liệu huấn luyện** phục vụ fine-tune / preference-tune model chính của Business AI Agent từ research, tương tác thực tế, trace agent, feedback và expert demonstrations
- **Quản trị vòng đời dataset**: raw event → cleaned example → reviewed example → versioned dataset → eval set → model release decision
- **Tách rõ RAG vs fine-tune**: research thô dùng cho retrieval, còn fine-tune dùng các ví dụ hành vi đã làm sạch, gắn nhãn và có provenance
- **Tự host hoàn toàn**, không phụ thuộc dịch vụ bên ngoài

---

## 2. Cấu trúc dữ liệu

### 2.1. Research Item

Mỗi nghiên cứu là một đơn vị dữ liệu với các trường:

| Trường | Mô tả | Ví dụ |
|---|---|---|
| `id` | Định danh duy nhất | `RES-2026-001` |
| `title` | Tiêu đề nghiên cứu | "Multi-Agent Orchestration Patterns" |
| `type` | Loại nghiên cứu | `internal-research` hoặc `reference` |
| `status` | Trạng thái | `draft` / `in-review` / `approved` / `archived` |
| `authors` | Người thực hiện | `["Linh", "Minh"]` |
| `created_at` | Ngày tạo | `2026-07-01` |
| `updated_at` | Ngày cập nhật | `2026-07-05` |
| `tags` | Thẻ phân loại | `["multi-agent", "orchestration", "langgraph"]` |
| `summary` | Tóm tắt ngắn (2-3 câu) | "Nghiên cứu các pattern..." |
| `content` | Nội dung đầy đủ (Markdown) | ... |
| `source_url` | Link nguồn (nếu là tài liệu tham khảo) | `https://arxiv.org/...` |
| `attachments` | File đính kèm | PDFs, images, notebooks |
| `relations` | Liên kết tới items khác | `[{"target": "RES-2026-003", "type": "extends"}]` |
| `collection_method` | Phương thức thu thập | `manual` / `auto-collected` / `ai-researched` |
| `collector_source` | Nguồn thu thập (nếu auto) | `arxiv` / `openai_blog` / `github_trending` |
| `evaluation` | Kết quả đánh giá AI (nếu auto) | `{overall_score: 85, relevance: 90, ...}` |
| `training_usage` | Cách item được phép dùng cho training | `rag-only` / `synthetic-seed` / `sft-approved` / `eval-only` |
| `license_policy` | Chính sách license/consent khi dùng dữ liệu | `internal` / `public-permissive` / `restricted` |
| `sensitive_level` | Mức nhạy cảm dữ liệu | `public` / `internal` / `confidential` / `pii` |

### 2.2. Phân loại chi tiết

#### Tài liệu do người thu thập (Human-collected)
- Thí nghiệm, benchmark, proof-of-concept của team
- Phân tích so sánh các framework/approach
- Bài học rút ra từ dự án thực tế
- Design decisions và architecture records
- Tài liệu tham khảo do team member tự tìm và thêm vào
- **AI-generated deep research** — báo cáo tổng hợp do Research Agent tạo ra khi phát hiện knowledge gap (có human review)

#### Tài liệu do AI thu thập (AI-collected)
- Academic papers (arXiv, conferences) — tự động crawl và đánh giá
- Blog posts từ các team khác (OpenAI, Anthropic, LangChain...) — RSS/API
- Documentation của frameworks — tự động index
- Case studies từ doanh nghiệp — web scraping
- Community insights — discussions từ Hacker News, Reddit, X/Twitter
- **Tự động thêm vào Knowledge Graph** sau khi evaluate, không cần human review
- **Phân biệt rõ** trong UI và graph (icon/badge khác với human-collected)

#### Dữ liệu phục vụ fine-tune (Training data)
- **Production conversations**: request/response thực tế của Business AI Agent
- **Agent traces**: tool calls, retrieved context, tool results, retry/failure modes
- **Human corrections**: output trước/sau khi reviewer sửa, kèm nhãn lỗi
- **Expert demonstrations**: ví dụ do team tạo thủ công để dạy agent hành vi chuẩn
- **Preference pairs**: chosen/rejected responses để train preference hoặc reward model
- **Eval failures**: case agent fail được giữ làm regression tests hoặc hard negatives
- **Synthetic examples**: ví dụ sinh từ approved research/SOP nhưng phải gắn provenance và review sample
- **Không trộn lẫn với research thô**: research item là nguồn kiến thức; training example là hành vi cụ thể đã làm sạch và được phép train

### 2.3. Nguồn thu thập (Auto-Collector Sources)

| Tier | Nguồn | Phương thức | Nội dung |
|---|---|---|---|
| **Academic** | arXiv, Semantic Scholar, Papers With Code, ACL Anthology | API | Papers, citations, code |
| **Industry** | OpenAI Blog, Anthropic, Google AI, LangChain, LlamaIndex | RSS | Research, best practices |
| **Community** | GitHub Trending, Hacker News, Reddit, Dev.to | API + Scraping | Repos, discussions, tutorials |
| **Business** | McKinsey, BCG, Gartner, Product Hunt | Scraping | Reports, case studies, products |
| **Social** | X/Twitter, YouTube, Podcasts | API + Whisper | Announcements, talks, transcripts |
| **Agent Runtime** | Business AI Agent logs, tool traces, eval failures | Event API | Fine-tuning examples, tool-calling traces |
| **Human Review** | Corrections, preference labels, expert demos | Internal UI | SFT, preference tuning, eval sets |
| **Business Ops** | CRM notes, support tickets, sales calls, proposals | Connector + anonymization | Domain task examples |

### 2.4. Quan hệ giữa các Research Items

| Loại quan hệ | Ý nghĩa | Ví dụ |
|---|---|---|
| `references` | Tham chiếu tới | Paper A được trích dẫn trong research B |
| `extends` | Mở rộng | Research B phát triển từ research A |
| `contradicts` | Mâu thuẫn | Kết quả B trái ngược với A |
| `supports` | Ủng hộ | B xác nhận kết luận của A |
| `depends-on` | Phụ thuộc | B cần kết quả của A để thực hiện |
| `inspired-by` | Lấy cảm hứng | B được gợi ý từ A |
| `collected-with` | Cùng thu thập từ một nguồn/batch | A và B cùng được collector tìm thấy |
| `synthesized-into` | Được tổng hợp thành | Nhiều items → 1 deep research report |
| `used-as-training-seed` | Research/SOP được dùng để tạo training examples | Research A → synthetic examples batch |
| `supports-eval-case` | Research item làm căn cứ cho eval case | Research A → eval case B |

### 2.5. Training Data Entities

| Entity | Mô tả | Ví dụ |
|---|---|---|
| `Training Event` | Raw event từ agent runtime, human review hoặc import | một session sales agent |
| `Training Example` | Example đã làm sạch theo format train | instruction SFT, tool-call trace |
| `Preference Pair` | Hai response cho cùng prompt với chosen/rejected | response A tốt hơn response B |
| `Dataset Version` | Tập examples được đóng gói và version | `business-agent-sft-v0.1` |
| `Eval Case` | Test case cố định có rubric | tool call correctness for CRM lookup |
| `Redaction Record` | Log PII/secret đã được mask | email, phone, API key |
| `Model Eval Run` | Kết quả đánh giá model trên dataset | baseline vs fine-tuned model |

### 2.6. Training Data Lifecycle

```
Raw event / trace / correction / research seed
        │
        ▼
PII redaction + policy check
        │
        ▼
Quality scoring + deduplication
        │
        ▼
AI pre-label + human review when needed
        │
        ▼
Training example
        │
        ├── SFT dataset
        ├── preference dataset
        ├── tool-calling dataset
        └── eval / holdout set
```

---

## 3. Knowledge Graph

### 3.1. Các loại Node

| Loại node | Mô tả | Ví dụ |
|---|---|---|
| **Research Item** | Một nghiên cứu cụ thể | "RAG Pipeline Optimization" |
| **Concept/Topic** | Khái niệm, chủ đề | "Retrieval-Augmented Generation", "Tool Use", "Memory" |
| **Technology** | Framework, thư viện, tool | "LangChain", "CrewAI", "AutoGen", "OpenAI API" |
| **Person** | Tác giả, researcher | "Linh", "Minh", "Andrew Ng" |
| **Business Domain** | Lĩnh vực ứng dụng | "Customer Service", "Sales", "Data Analysis" |
| **Agent Pattern** | Pattern thiết kế agent | "ReAct", "Plan-and-Execute", "Multi-Agent Debate" |
| **Collector Source** | Nguồn thu thập tự động | "arXiv", "OpenAI Blog", "GitHub Trending" |
| **Research Gap** | Knowledge gap được phát hiện | "Agent Security Best Practices" (chưa có research) |
| **Training Example** | Ví dụ đã duyệt để train/eval model | "sales lead qualification trace" |
| **Dataset Version** | Dataset đã đóng gói theo version | "business-agent-sft-v0.1" |
| **Eval Case** | Test case/rubric cố định | "CRM tool call must happen before lead scoring" |
| **Agent Trace** | Trace từ Business AI Agent runtime | "task-456 tool sequence" |
| **Business Task** | Loại tác vụ business agent phải làm tốt | "lead qualification", "support escalation" |

### 3.2. Các loại Edge

| Edge | Từ → Đến | Ý nghĩa |
|---|---|---|
| `researches` | Research Item → Concept | Nghiên cứu này khảo sát khái niệm này |
| `uses_tech` | Research Item → Technology | Nghiên cứu sử dụng công nghệ này |
| `authored_by` | Research Item → Person | Nghiên cứu được viết bởi |
| `applies_to` | Research Item → Business Domain | Áp dụng cho lĩnh vực này |
| `implements_pattern` | Research Item → Agent Pattern | Triển khai pattern này |
| `collected_from` | Research Item → Collector Source | Được thu thập tự động từ nguồn này |
| `related_to` | Concept ↔ Concept | Hai khái niệm liên quan nhau |
| `prerequisite_of` | Concept → Concept | Khái niệm A là tiền đề của B |
| `references` | Research Item → Research Item | Tham chiếu giữa các nghiên cứu |
| `extends` | Research Item → Research Item | Mở rộng nghiên cứu trước |
| `contradicts` | Research Item → Research Item | Kết quả mâu thuẫn |
| `supports` | Research Item → Research Item | Xác nhận lẫn nhau |
| `fills_gap` | Research Item → Research Gap | Nghiên cứu này lấp đầy gap này |
| `synthesized_from` | Research Item → Research Items | Report tổng hợp từ nhiều items |
| `generates_training_examples` | Research Item → Training Example | Research/SOP được dùng để tạo example |
| `included_in_dataset` | Training Example → Dataset Version | Example nằm trong dataset version |
| `evaluated_by` | Dataset Version → Eval Case | Dataset/model được kiểm bằng eval case |
| `derived_from_trace` | Training Example → Agent Trace | Example tạo từ trace thực tế |
| `teaches_task` | Training Example → Business Task | Example dạy model task cụ thể |

### 3.3. Topic Clusters gợi ý cho AI Agents for Business

```
AI Agents for Business
├── Agent Architecture
│   ├── Single Agent (ReAct, Tool Use, Function Calling)
│   ├── Multi-Agent Systems (Orchestration, Debate, Collaboration)
│   ├── Agent Memory (Short-term, Long-term, Episodic, Semantic)
│   └── Planning & Reasoning (CoT, ToT, Plan-and-Execute)
├── Core Capabilities
│   ├── RAG (Retrieval-Augmented Generation)
│   ├── Tool Use & Function Calling
│   ├── Code Generation & Execution
│   ├── Web Browsing & Scraping
│   └── Vision & Multimodal
├── Business Applications
│   ├── Customer Service Agents
│   ├── Sales & Lead Generation
│   ├── Data Analysis & Reporting
│   ├── Document Processing
│   ├── Workflow Automation
│   └── Decision Support
├── Infrastructure & Ops
│   ├── LLM Selection & Routing
│   ├── Prompt Engineering & Management
│   ├── Evaluation & Testing
│   ├── Monitoring & Observability
│   ├── Cost Optimization
│   └── Security & Guardrails
├── Model Improvement & Training
│   ├── SFT Datasets
│   ├── Preference Data
│   ├── Tool-Calling Traces
│   ├── Eval Sets & Rubrics
│   ├── PII Redaction
│   └── Model Release Gates
└── Frameworks & Tools
    ├── LangChain / LangGraph
    ├── CrewAI
    ├── AutoGen / AG2
    ├── Semantic Kernel
    ├── Dify / Coze
    └── Custom Frameworks
```

---

## 4. Tech Stack (Self-Hosted)

### 4.1. Kiến trúc tổng thể

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │ Research  │ │  Graph   │ │  Search  │ │Dashboard │ │ Collector │ │
│  │  Editor   │ │  Viewer  │ │   View   │ │ & Stats  │ │  Manager  │ │
│  │ Training  │ │ Dataset  │ │  Eval    │ │ Review   │ │ Export    │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────┘ │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ REST / GraphQL
┌───────────────────────────┴──────────────────────────────────────────┐
│                     Backend (Python/FastAPI)                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐ │
│  │  CRUD    │ │  Graph   │ │  Search  │ │   LLM    │ │ Collector │ │
│  │   API    │ │  Engine  │ │  Engine  │ │ Pipeline │ │  Engine   │ │
│  │Training │ │ Dataset  │ │  Eval    │ │ Redact   │ │  Export   │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────┘ │
└──┬─────────────┬─────────────┬──────────────┬──────────────┬────────┘
   │             │             │              │              │
┌──┴──┐   ┌─────┴────┐ ┌─────┴─────┐ ┌──────┴─────┐ ┌─────┴──────┐
│PgSQL│   │  Neo4j   │ │Meilisearch│ │   Ollama   │ │  Browser-  │
│+vec │   │ (graph)  │ │ (search)  │ │   (LLM)    │ │   less     │
└─────┘   └──────────┘ └───────────┘ └────────────┘ │ (scraping) │
                                                     └────────────┘
                         ┌────────────┐ ┌────────────┐
                         │  MinIO     │ │ Labeling   │
                         │ datasets   │ │ / Review   │
                         └────────────┘ └────────────┘
```

### 4.2. Chi tiết từng layer

#### Frontend
| Component | Công nghệ | Lý do |
|---|---|---|
| Framework | **Next.js 14+** (App Router) | SSR, API routes, ecosystem lớn |
| Graph Visualization | **Cytoscape.js** hoặc **D3.js** | Interactive, customizable, performant |
| Markdown Editor | **Milkdown** hoặc **Tiptap** | WYSIWYG + Markdown, extensible |
| Training Review UI | **Custom React tables + diff viewer** | Review examples, compare before/after, preference labeling |
| Dataset Dashboard | **Recharts / Tremor** | Dataset health, label distribution, eval metrics |
| UI Library | **shadcn/ui + Tailwind CSS** | Đẹp, accessible, dễ customize |
| State Management | **Zustand** | Lightweight, đơn giản |

#### Backend
| Component | Công nghệ | Lý do |
|---|---|---|
| Framework | **FastAPI** (Python) | Async, nhanh, auto-docs, AI ecosystem |
| Graph DB | **Neo4j Community Edition** | Graph-native, Cypher query language mạnh |
| Relational DB | **PostgreSQL + pgvector** | Metadata + vector search trong 1 DB |
| Search | **Meilisearch** | Fast, typo-tolerant, self-hosted dễ |
| AI/LLM | **Ollama** (local LLM) | Evaluation, tagging, summarization, extraction |
| Embeddings | **sentence-transformers** | Semantic search + deduplication, chạy local |
| Task Queue | **Celery + Redis** | Collector jobs, re-index, background processing |
| Scheduler | **APScheduler** | Cron-based collector scheduling |
| Web Scraping | **Playwright + Browserless** | Headless browser cho dynamic pages |
| PDF Processing | **Marker / Nougat** | PDF → Markdown conversion |
| Content Extraction | **trafilatura / readability** | HTML → clean text extraction |
| PII Redaction | **Microsoft Presidio** hoặc custom NER rules | Mask email, phone, name, secret trước khi train |
| Dataset Export | **JSONL / Parquet / HuggingFace Datasets** | Format chuẩn cho fine-tune/evaluation |
| Experiment Tracking | **MLflow** hoặc file-based registry | Track dataset version, eval run, model candidate |
| Data Validation | **Great Expectations** hoặc custom checks | Kiểm tra schema, leakage, duplicate, split integrity |

#### Infrastructure
| Component | Công nghệ | Lý do |
|---|---|---|
| Containerization | **Docker Compose** | Dễ setup, reproducible |
| Reverse Proxy | **Caddy** hoặc **Nginx** | Auto HTTPS, routing |
| File Storage | **MinIO** (S3-compatible) | Self-hosted object storage (PDFs, attachments) |
| Auth | **Keycloak** hoặc **Better Auth** | SSO, team management |
| Monitoring | **Prometheus + Grafana** | Collector health, system metrics |
| Dataset Storage | **MinIO + PostgreSQL metadata** | Lưu exported datasets, eval artifacts, model reports |
| Optional Labeling Tool | **Label Studio** | Dùng nếu cần labeling UI mạnh hơn custom UI |

### 4.3. Alternative: Lightweight Stack

Nếu team nhỏ (< 5 người) và muốn setup nhanh:

| Layer | Công nghệ | Lý do |
|---|---|---|
| Frontend + Backend | **Next.js fullstack** | Một codebase, deploy đơn giản |
| Database | **PostgreSQL + pgvector** | Data + vector search trong 1 DB |
| Graph | **pg_graph** extension hoặc build graph từ relations table | Không cần Neo4j riêng |
| Search | **PostgreSQL full-text search + pg_trgm** | Không cần Meilisearch riêng |
| AI | **Ollama** | Vẫn giữ local LLM |
| Training Data | **PostgreSQL tables + JSONL export** | Chưa cần Label Studio/MLflow riêng |
| Collector | **APScheduler + Playwright** | Vẫn giữ auto-collector, ít sources hơn |
| Deploy | **Docker Compose** | 2-3 containers thay vì 6-7 |

---

## 5. Tính năng chi tiết

### 5.1. CRUD Research Items
- Tạo, sửa, xóa research items (thủ công)
- Markdown editor với preview real-time
- Upload attachments (PDFs, images, notebooks)
- YAML/JSON frontmatter cho metadata
- Import từ URL (auto-extract metadata từ arXiv, blog posts...)
- Export ra Markdown, PDF, JSON
- Phân biệt rõ items tạo thủ công vs auto-collected

### 5.2. Knowledge Graph Visualization
- **Interactive graph**: kéo thả, zoom, pan
- **Filter nodes** theo loại (research, concept, tech, person, collector source, gap)
- **Highlight paths** giữa 2 nodes bất kỳ
- **Cluster view**: nhóm nodes theo topic/domain
- **Timeline mode**: hiển thị nodes theo thời gian
- **Ego graph**: click vào 1 node → hiện tất cả kết nối trực tiếp
- **Node size** phản ánh số lượng kết nối (importance)
- **Edge labels** hiển thị loại quan hệ
- **Search within graph**: tìm node và focus vào nó
- **Collector source overlay**: hiển thị items đến từ nguồn nào
- **Gap visualization**: highlight areas chưa có research

### 5.3. Search & Discovery
- **Full-text search**: tìm trong title, content, tags
- **Semantic search**: tìm theo ý nghĩa (dùng embeddings)
- **Graph-based recommendations**: "Nghiên cứu liên quan" dựa trên graph connections
- **Filter** theo type, status, author, date range, tags, collection method, source
- **Saved queries**: lưu các search thường dùng
- **Trending search**: topics đang được thu thập nhiều gần đây

### 5.4. AI-Powered Features
- **Auto-tagging**: LLM tự extract concepts/topics từ nội dung
- **Auto-summarization**: tạo tóm tắt ngắn từ nội dung dài
- **Concept extraction**: tự động nhận diện concepts mới để thêm vào graph
- **Relation suggestion**: gợi ý quan hệ giữa research items dựa trên nội dung
- **Gap analysis**: phát hiện topics chưa có research hoặc research ít
- **Q&A over research**: hỏi đáp dựa trên toàn bộ knowledge base (RAG)
- **Feedback learning**: AI cải thiện scoring dựa trên human review decisions

### 5.5. AI Auto-Collector (Thu thập tự động)
- **Multi-source crawling**: tự động thu thập từ arXiv, blogs, GitHub, RSS, HN, Reddit, X/Twitter...
- **Scheduled collection**: chạy theo cron (hàng giờ / hàng ngày / hàng tuần tùy nguồn)
- **Content extraction**: PDF → Markdown, HTML → clean text, GitHub repo → README + metadata
- **AI relevance scoring**: đánh giá 5 tiêu chí (Relevance, Quality, Novelty, Actionability, Freshness)
- **Auto-ingest**: tài liệu đạt threshold → tự động thêm vào Knowledge Graph, không cần human review
- **Phân loại rõ ràng**: badge/tag "AI-collected" vs "Human-collected" trong UI và graph
- **3-layer deduplication**: URL match → Fingerprint → Semantic similarity
- **Auto-enrichment**: summarize, extract concepts, find relations, generate tags
- **Auto-download**: tải PDFs, attachments về lưu trữ local
- **Source management UI**: thêm/sửa/xóa/tắt nguồn thu thập
- **Collector health monitoring**: dashboard hiển thị trạng thái từng source
- **Knowledge Gap Detection**: AI phân tích graph để phát hiện topics thiếu research
- **Gap-based human-in-the-loop**: khi phát hiện gap lớn → đề xuất team member research hoặc AI tự deep research (chỉ ở đây mới cần human approval)
- **Trend detection**: phát hiện topics đang trending từ collected items

### 5.6. Collaboration
- **Gap-based review workflow**: AI phát hiện gap → đề xuất research → human approve/assign
- **Deep research approval**: khi AI tự deep research để fill gap → human review report trước khi publish
- **Manual items review**: draft → in-review → approved (cho items do người viết)
- **AI-collected items**: tự động ingest, không cần review (chỉ monitor qua dashboard)
- **Assign researcher** cho gap topics
- **Comments** trên từng research item
- **Version history**: track thay đổi, rollback
- **Activity feed**: ai đã thêm/sửa gì gần đây + AI đã thu thập gì
- **Weekly digest**: email/notification tổng hợp research mới (cả manual + auto-collected) + gaps phát hiện
- **Flag for discussion**: đánh dấu items cần team thảo luận
- **Request deep dive**: yêu cầu team member viết internal research về topic AI tìm được

### 5.7. Dashboard & Analytics
- **Stats overview**: tổng số research, theo loại, theo tháng, theo collection method
- **Active contributors**: ai đang research nhiều nhất
- **Topic coverage heatmap**: topic nào được research nhiều/ít
- **Knowledge gaps**: danh sách topics cần research thêm (AI phát hiện)
- **Trending topics**: topics đang được quan tâm gần đây (từ collector data)
- **Graph health**: density, connected components, isolated nodes
- **Collector stats**: items discovered/evaluated/approved/rejected per day
- **Source health**: trạng thái từng collector source (last run, errors, items found)
- **Score distribution**: phân bố điểm đánh giá (tuần/tháng)
- **Cost tracking**: chi phí LLM inference cho evaluation
- **Training data health**: số examples theo domain/task/source/label/split
- **Dataset version metrics**: số lượng examples, train/validation/test split, synthetic ratio, PII status
- **Model eval comparison**: baseline vs fine-tuned model theo task completion, tool-call correctness, groundedness, safety
- **Data quality alerts**: duplicate rate cao, PII chưa redact, eval leakage, thiếu examples cho domain quan trọng

### 5.8. Fine-tuning Data Collection

Hệ thống Research nên có thêm một lớp **Training Data Hub** để gom, làm sạch, gắn nhãn và xuất dataset phục vụ fine-tune model chính của Business AI Agent.

Mục tiêu không phải đưa toàn bộ research thô vào fine-tune. Research thô phù hợp hơn cho RAG. Fine-tune nên dùng các ví dụ hành vi cụ thể: cách agent phân tích bài toán business, hỏi lại khi thiếu thông tin, gọi tool, lập kế hoạch, viết output đúng format, xử lý lỗi, và phản hồi theo chuẩn của team.

#### Nguồn dữ liệu nên thu thập

| Nguồn | Dữ liệu thu được | Dùng cho |
|---|---|---|
| Production conversations | User request, agent response, feedback, outcome | SFT, preference tuning, regression eval |
| Agent traces | Reasoning summary, tool calls, tool results, retry, failure mode | Tool-calling fine-tune, workflow imitation |
| Human expert demonstrations | Expert tự làm mẫu: prompt, plan, tool usage, final output | High-quality SFT |
| Human corrections | Before/after response, reviewer note, issue type | Preference tuning, error correction dataset |
| Research items | Concepts, summaries, best practices, examples | Synthetic instruction generation, domain adaptation |
| SOPs / playbooks | Quy trình tư vấn, sales, support, analytics, operations | Task decomposition and output format training |
| Customer/project artifacts | Brief, transcript, CRM note, proposal, report | Domain-specific task examples sau khi anonymize |
| Eval failures | Cases model trả lời sai hoặc tool call sai | Hard negative set, regression eval |
| Successful workflows | Completed tasks có outcome tốt | Workflow cloning |
| User ratings | thumbs up/down, score, free-text feedback | Preference dataset |

#### Loại dataset cần tạo

| Dataset type | Format | Ví dụ |
|---|---|---|
| Instruction SFT | `instruction`, `context`, `response` | "Tóm tắt pain points từ sales call này..." |
| Multi-turn chat SFT | `messages[]` | Cuộc hội thoại tư vấn khách hàng nhiều lượt |
| Tool-calling SFT | `messages[]`, `tools[]`, `tool_calls[]`, `tool_results[]` | Agent gọi CRM/search/calculator đúng lúc |
| Preference dataset | `prompt`, `chosen`, `rejected`, `reason` | Response A tốt hơn vì có action plan rõ |
| Error correction | `bad_response`, `critique`, `fixed_response` | Sửa hallucination, format sai, thiếu bước |
| Domain Q&A | `question`, `answer`, `citations` | Trả lời dựa trên research được approve |
| Workflow traces | `goal`, `steps`, `tool_sequence`, `final_output`, `outcome` | Tạo proposal, phân tích lead, xử lý ticket |
| Evaluation set | `input`, `expected_behavior`, `rubric` | Bộ test cố định cho model trước/sau fine-tune |

#### Data capture trong Business AI Agent

Business AI Agent chính cần log có cấu trúc cho mỗi task:

```json
{
  "session_id": "sess_123",
  "task_id": "task_456",
  "user_id": "user_001",
  "business_domain": "sales",
  "task_type": "lead_qualification",
  "messages": [],
  "tool_calls": [],
  "tool_results": [],
  "retrieved_context": [],
  "final_output": "...",
  "user_feedback": {
    "rating": 5,
    "comment": "Good structure, but missing budget analysis"
  },
  "human_review": {
    "decision": "edited",
    "edited_output": "...",
    "labels": ["missing_budget_analysis", "good_tone"]
  },
  "outcome": {
    "status": "successful",
    "business_metric": "lead_accepted"
  }
}
```

#### Training Data Pipeline

```
Raw interaction / trace / research / SOP
        │
        ▼
Capture structured event
        │
        ▼
PII redaction + anonymization
        │
        ▼
License / consent / source policy check
        │
        ▼
Quality scoring
        │
        ▼
Deduplication + near-duplicate detection
        │
        ▼
Labeling / human review / AI-assisted critique
        │
        ▼
Convert to target dataset format
        │
        ▼
Dataset versioning
        │
        ▼
Export to JSONL / Parquet / HuggingFace format
        │
        ▼
Train / fine-tune / evaluate
```

#### Quality labels nên chuẩn hóa

| Label group | Examples |
|---|---|
| Task quality | `complete`, `partially_complete`, `wrong_intent`, `missing_context` |
| Business quality | `actionable`, `generic`, `wrong_priority`, `good_business_judgment` |
| Tool use | `correct_tool`, `wrong_tool`, `missing_tool`, `tool_retry_success`, `tool_error_unhandled` |
| Factuality | `grounded`, `unsupported_claim`, `contradicts_context`, `needs_citation` |
| Format | `matches_template`, `format_error`, `too_verbose`, `too_short` |
| Safety/privacy | `contains_pii`, `leaks_secret`, `unsafe_advice`, `needs_escalation` |
| Tone | `professional`, `too_salesy`, `too_casual`, `unclear` |

#### Dataset governance

- Không fine-tune trực tiếp trên dữ liệu có PII, secret, customer confidential data chưa được anonymize.
- Không đưa nội dung copyrighted dài vào fine-tune nếu license không cho phép.
- Lưu provenance cho từng training example: source, timestamp, reviewer, transform version, consent/license.
- Mỗi example phải có `dataset_split`: `train`, `validation`, `test`, `holdout`.
- Test/holdout set không được dùng để generate synthetic training examples.
- Dataset phải version rõ ràng: `business-agent-sft-v0.1`, `tool-calling-v0.2`, `preference-v0.1`.
- Khi model mới kém hơn trên eval set cũ, không promote model.

#### Human review workflow

```
Candidate example
        │
        ▼
AI pre-label + quality score
        │
        ├─ low quality -> reject
        ├─ obvious high quality -> auto-accept into draft dataset
        └─ uncertain/high-impact -> human review
                │
                ├─ accept
                ├─ edit and accept
                ├─ reject
                └─ mark as eval-only
```

#### UI cần có cho Training Data Hub

- **Dataset Builder**: chọn source, filter domain/task/quality, tạo dataset version.
- **Example Review Queue**: review candidate examples, compare original vs cleaned vs formatted.
- **PII Redaction View**: highlight thông tin nhạy cảm đã bị mask.
- **Trace Viewer**: xem messages, retrieved context, tool calls, errors, final output.
- **Preference Labeling UI**: so sánh 2 responses và chọn response tốt hơn kèm lý do.
- **Rubric Editor**: định nghĩa tiêu chí chấm cho từng task type.
- **Dataset Health Dashboard**: số lượng examples theo domain, task type, label, split, source.
- **Model Eval Dashboard**: so sánh baseline vs fine-tuned model theo từng capability.
- **Export Manager**: xuất JSONL/Parquet theo format của framework train.

#### API endpoints gợi ý

```
POST   /api/training/events                     # ingest raw interaction/trace
GET    /api/training/candidates                 # list candidate examples
POST   /api/training/candidates/{id}/accept
POST   /api/training/candidates/{id}/reject
PUT    /api/training/candidates/{id}/edit

GET    /api/training/datasets
POST   /api/training/datasets
GET    /api/training/datasets/{id}
POST   /api/training/datasets/{id}/build
POST   /api/training/datasets/{id}/export

GET    /api/training/evals
POST   /api/training/evals/run
GET    /api/training/evals/{run_id}

POST   /api/training/redact
POST   /api/training/synthetic/generate
POST   /api/training/preferences
```

#### Database tables bổ sung

```sql
CREATE TABLE training_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    session_id TEXT,
    task_id TEXT,
    business_domain TEXT,
    task_type TEXT,
    raw_payload JSONB NOT NULL,
    pii_status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE training_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES training_events(id),
    example_type TEXT NOT NULL,
    business_domain TEXT,
    task_type TEXT,
    input JSONB NOT NULL,
    output JSONB,
    labels TEXT[],
    quality_score NUMERIC,
    status TEXT NOT NULL DEFAULT 'candidate',
    reviewer_id UUID,
    provenance JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE training_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    purpose TEXT NOT NULL,
    selection_query JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (name, version)
);

CREATE TABLE training_dataset_examples (
    dataset_id UUID REFERENCES training_datasets(id) ON DELETE CASCADE,
    example_id UUID REFERENCES training_examples(id) ON DELETE CASCADE,
    split TEXT NOT NULL CHECK (split IN ('train', 'validation', 'test', 'holdout')),
    PRIMARY KEY (dataset_id, example_id)
);

CREATE TABLE preference_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt JSONB NOT NULL,
    chosen JSONB NOT NULL,
    rejected JSONB NOT NULL,
    reason TEXT,
    labeler_id UUID,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

#### Synthetic data generation từ Research System

Research items có thể dùng để tạo dữ liệu synthetic, nhưng cần kiểm soát chất lượng:

- Từ một research item, tạo 5-20 task thực tế liên quan đến business agent.
- Sinh nhiều format output: executive summary, implementation plan, risk analysis, comparison table, customer-facing answer.
- Sinh negative examples: câu trả lời thiếu citation, quá generic, sai tool, sai format.
- Human review sample theo tỷ lệ, ví dụ review 20% synthetic examples mỗi batch.
- Synthetic examples phải gắn `synthetic=true` và không trộn vào eval holdout.

Ví dụ:

```json
{
  "instruction": "Dựa trên research về multi-agent orchestration, đề xuất architecture cho agent xử lý customer support tier-2.",
  "context": "Summary + key findings from approved research items...",
  "response": "Architecture gồm router agent, retrieval agent, escalation agent...",
  "labels": ["architecture_design", "customer_support", "multi_agent"],
  "source_research_ids": ["RES-2026-042", "RES-2026-057"],
  "synthetic": true
}
```

#### Eval trước khi fine-tune

Trước mỗi lần train, hệ thống nên build eval set cố định:

- Business task completion.
- Tool call correctness.
- Groundedness/citation correctness.
- Format adherence.
- Safety/privacy.
- Domain-specific judgment.
- Latency/cost nếu model được deploy production.

Chỉ promote model nếu:

- Tăng chất lượng trên target tasks.
- Không giảm safety/privacy.
- Không giảm mạnh trên general tasks.
- Không làm agent gọi tool sai nhiều hơn.

---

## 6. Database Schema

### 6.1. PostgreSQL Tables

```sql
-- Research items
CREATE TABLE research_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    type VARCHAR(20) NOT NULL CHECK (type IN ('internal-research', 'reference')),
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'in-review', 'approved', 'archived')),
    summary TEXT,
    content TEXT,
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    search_vector tsvector,  -- for full-text search

    -- Auto-collector fields
    collection_method VARCHAR(20) DEFAULT 'manual'
        CHECK (collection_method IN ('manual', 'auto-collected', 'ai-researched')),
    collector_source VARCHAR(50),  -- 'arxiv', 'openai_blog', 'github_trending', etc.
    external_id TEXT,              -- ID from source (arxiv ID, GitHub repo name, etc.)
    collected_at TIMESTAMPTZ,      -- When auto-collected

    -- AI evaluation scores (for auto-collected items)
    eval_overall_score FLOAT,
    eval_relevance_score FLOAT,
    eval_quality_score FLOAT,
    eval_novelty_score FLOAT,
    eval_actionability_score FLOAT,
    eval_freshness_score FLOAT,
    eval_reasoning TEXT,           -- LLM's reasoning for the scores
    eval_suggested_tags TEXT[],
    eval_suggested_relations JSONB
);

-- Authors (many-to-many)
CREATE TABLE research_authors (
    research_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'author',  -- author, reviewer, contributor
    PRIMARY KEY (research_id, user_id)
);

-- Tags
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    type VARCHAR(20)  -- topic, technology, domain, pattern
);

CREATE TABLE research_tags (
    research_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (research_id, tag_id)
);

-- Relations between research items
CREATE TABLE research_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    target_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    relation_type VARCHAR(20) NOT NULL
        CHECK (relation_type IN ('references', 'extends', 'contradicts',
                                  'supports', 'depends-on', 'inspired-by',
                                  'collected-with', 'synthesized-into')),
    discovered_by VARCHAR(20) DEFAULT 'manual',  -- 'manual' or 'ai'
    confidence FLOAT,  -- AI confidence score for auto-discovered relations
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Attachments
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type VARCHAR(100),
    size_bytes BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Review comments
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    author_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Version history
CREATE TABLE research_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    version INT NOT NULL,
    title TEXT,
    content TEXT,
    changed_by UUID REFERENCES users(id),
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    change_note TEXT
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role VARCHAR(20) DEFAULT 'member',  -- admin, member, viewer
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw events for fine-tuning data collection
CREATE TABLE training_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(50) NOT NULL,  -- agent_runtime, human_review, research_synthetic, import
    session_id TEXT,
    task_id TEXT,
    business_domain VARCHAR(100),
    task_type VARCHAR(100),
    raw_payload JSONB NOT NULL,
    pii_status VARCHAR(20) DEFAULT 'pending'
        CHECK (pii_status IN ('pending', 'redacted', 'blocked')),
    policy_status VARCHAR(20) DEFAULT 'pending'
        CHECK (policy_status IN ('pending', 'allowed', 'restricted', 'blocked')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cleaned and labeled examples ready for dataset building
CREATE TABLE training_examples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES training_events(id) ON DELETE SET NULL,
    example_type VARCHAR(50) NOT NULL
        CHECK (example_type IN ('instruction-sft', 'chat-sft', 'tool-calling',
                                'preference', 'error-correction', 'eval-case')),
    business_domain VARCHAR(100),
    task_type VARCHAR(100),
    input JSONB NOT NULL,
    output JSONB,
    labels TEXT[],
    quality_score FLOAT,
    synthetic BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'candidate'
        CHECK (status IN ('candidate', 'accepted', 'rejected', 'eval-only', 'archived')),
    reviewer_id UUID REFERENCES users(id),
    provenance JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dataset versions for fine-tuning/evaluation
CREATE TABLE training_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    purpose VARCHAR(50) NOT NULL,  -- sft, preference, tool-calling, eval
    selection_query JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'draft'
        CHECK (status IN ('draft', 'built', 'exported', 'archived')),
    export_path TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (name, version)
);

CREATE TABLE training_dataset_examples (
    dataset_id UUID REFERENCES training_datasets(id) ON DELETE CASCADE,
    example_id UUID REFERENCES training_examples(id) ON DELETE CASCADE,
    split VARCHAR(20) NOT NULL CHECK (split IN ('train', 'validation', 'test', 'holdout')),
    PRIMARY KEY (dataset_id, example_id)
);

-- Preference pairs for chosen/rejected response training
CREATE TABLE preference_pairs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    example_id UUID REFERENCES training_examples(id) ON DELETE CASCADE,
    prompt JSONB NOT NULL,
    chosen JSONB NOT NULL,
    rejected JSONB NOT NULL,
    reason TEXT,
    labeler_id UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Model evaluation runs against fixed datasets/rubrics
CREATE TABLE model_eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name TEXT NOT NULL,
    model_version TEXT,
    dataset_id UUID REFERENCES training_datasets(id),
    metrics JSONB NOT NULL,
    report_path TEXT,
    promotion_decision VARCHAR(20)
        CHECK (promotion_decision IN ('pending', 'promote', 'reject', 'needs-review')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6.2. Neo4j Graph Model

```cypher
// Node labels
(:ResearchItem {id, title, type, status, date})
(:Concept {id, name, description})
(:Technology {id, name, category})
(:Person {id, name, role})
(:BusinessDomain {id, name})
(:AgentPattern {id, name, description})
(:CollectorSource {id, name, type, schedule})
(:ResearchGap {id, name, priority, status})
(:TrainingExample {id, example_type, task_type, status, quality_score})
(:DatasetVersion {id, name, version, purpose})
(:EvalCase {id, task_type, rubric})
(:AgentTrace {id, session_id, task_id})
(:BusinessTask {id, name, domain})

// Relationship types
(:ResearchItem)-[:RESEARCHES {weight}]->(:Concept)
(:ResearchItem)-[:USES_TECH]->(:Technology)
(:ResearchItem)-[:AUTHORED_BY]->(:Person)
(:ResearchItem)-[:APPLIES_TO]->(:BusinessDomain)
(:ResearchItem)-[:IMPLEMENTS]->(:AgentPattern)
(:ResearchItem)-[:COLLECTED_FROM]->(:CollectorSource)
(:ResearchItem)-[:FILLS_GAP]->(:ResearchGap)
(:ResearchItem)-[:SYNTHESIZED_FROM]->(:ResearchItem)
(:ResearchItem)-[:REFERENCES]->(:ResearchItem)
(:ResearchItem)-[:EXTENDS]->(:ResearchItem)
(:ResearchItem)-[:CONTRADICTS]->(:ResearchItem)
(:ResearchItem)-[:SUPPORTS]->(:ResearchItem)
(:Concept)-[:RELATED_TO]->(:Concept)
(:Concept)-[:PREREQUISITE_OF]->(:Concept)
(:ResearchItem)-[:GENERATES_TRAINING_EXAMPLE]->(:TrainingExample)
(:TrainingExample)-[:INCLUDED_IN_DATASET {split}]->(:DatasetVersion)
(:TrainingExample)-[:DERIVED_FROM_TRACE]->(:AgentTrace)
(:TrainingExample)-[:TEACHES_TASK]->(:BusinessTask)
(:DatasetVersion)-[:EVALUATED_BY]->(:EvalCase)
```

### 6.3. Sync Strategy

```
User creates/updates research item  OR  Collector discovers new item
OR Business AI Agent emits training event
        │
        ▼
  PostgreSQL (source of truth)
        │
        ▼ (async via Celery task)
  ┌─────────────────────────┐
  │  1. Extract concepts     │ ← LLM auto-tagging
  │  2. Update Neo4j         │ ← sync graph nodes/edges
  │  3. Update search        │ ← re-index in Meilisearch
  │  4. Generate embeddings  │ ← vector embeddings
  │  5. Store fingerprint    │ ← deduplication
  │  6. Find relations       │ ← AI-suggested connections
  │  7. Redact PII           │ ← for training events/examples
  │  8. Build datasets       │ ← versioned JSONL/Parquet export
  │  9. Run evals            │ ← compare model candidates
  └─────────────────────────┘
```

---

## 7. API Design

### 7.1. Research Items

```
GET    /api/research                    # List all (with filters)
POST   /api/research                    # Create new
GET    /api/research/{id}               # Get one
PUT    /api/research/{id}               # Update
DELETE /api/research/{id}               # Delete
POST   /api/research/{id}/publish       # Change status to approved
GET    /api/research/{id}/versions      # Get version history
POST   /api/research/{id}/comments      # Add comment
GET    /api/research/{id}/evaluation    # Get AI evaluation details (auto-collected)
```

### 7.2. Graph

```
GET    /api/graph                       # Full graph data
GET    /api/graph/node/{id}             # Node + neighbors
GET    /api/graph/paths                 # Shortest path between 2 nodes
GET    /api/graph/cluster/{topic}       # Cluster around a topic
GET    /api/graph/stats                 # Graph statistics
GET    /api/graph/gaps                  # Knowledge gaps
GET    /api/graph/sources               # Collector source nodes + stats
```

### 7.3. Search

```
GET    /api/search?q=...               # Full-text search
POST   /api/search/semantic             # Semantic search (embedding)
GET    /api/search/suggest?q=...        # Autocomplete
GET    /api/search/trending             # Trending topics from collector
```

### 7.4. AI Features

```
POST   /api/ai/summarize               # Summarize content
POST   /api/ai/extract-concepts        # Extract concepts from text
POST   /api/ai/suggest-relations       # Suggest relations
POST   /api/ai/qa                      # Q&A over knowledge base
POST   /api/ai/deep-research           # Trigger deep research on a topic
```

### 7.5. Collector

```
GET    /api/collector/sources                    # List all sources
POST   /api/collector/sources                    # Add new source
PUT    /api/collector/sources/{id}               # Update source config
DELETE /api/collector/sources/{id}               # Remove source
POST   /api/collector/sources/{id}/run           # Trigger manual run
GET    /api/collector/sources/{id}/runs          # Run history

GET    /api/collector/queue                       # Get review queue
GET    /api/collector/queue/stats                 # Queue statistics
POST   /api/collector/queue/{id}/approve          # Approve item
POST   /api/collector/queue/{id}/reject           # Reject item
POST   /api/collector/queue/{id}/snooze           # Snooze item
PUT    /api/collector/queue/{id}/edit              # Edit before approve
POST   /api/collector/queue/batch-approve         # Batch approve

GET    /api/collector/stats                       # Overall collector stats
GET    /api/collector/stats/sources               # Per-source breakdown
GET    /api/collector/stats/timeline              # Items collected over time
```

### 7.6. Training Data & Fine-tune Dataset

```
POST   /api/training/events                       # Ingest raw agent interaction/trace
GET    /api/training/events                       # List raw events with PII/policy filters
POST   /api/training/events/{id}/redact           # Run PII redaction
POST   /api/training/events/{id}/convert          # Convert event to candidate example

GET    /api/training/examples                     # List candidate/accepted examples
GET    /api/training/examples/{id}                # View one example + provenance
PUT    /api/training/examples/{id}                # Edit cleaned example
POST   /api/training/examples/{id}/accept         # Approve for dataset
POST   /api/training/examples/{id}/reject         # Reject example
POST   /api/training/examples/{id}/eval-only      # Keep only for eval/holdout

POST   /api/training/preferences                  # Create chosen/rejected preference pair
GET    /api/training/preferences                  # List preference pairs

GET    /api/training/datasets                     # List dataset versions
POST   /api/training/datasets                     # Create dataset definition
POST   /api/training/datasets/{id}/build          # Materialize examples into splits
POST   /api/training/datasets/{id}/export         # Export JSONL/Parquet/HF format
GET    /api/training/datasets/{id}/health         # Dataset quality metrics

POST   /api/training/synthetic/generate           # Generate examples from approved research/SOP
POST   /api/training/evals/run                    # Run model eval on fixed dataset
GET    /api/training/evals/{run_id}               # Eval report and promotion decision
```

---

## 8. UI/UX Wireframes

### 8.1. Trang chính - Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│  🔍 Search...          [+ New Research]  [🤖 Collector]  👤 Linh    │
├──────────┬───────────────────────────────────────────────────────────┤
│          │                                                           │
│  📊 Stats│   Recent Research                                         │
│  ─────── │   ┌─────────────────────────────────────────────────────┐ │
│  Total: 89│   │ 📄 Multi-Agent Orchestration    [approved] manual │ │
│  Internal │   │    Linh · 2 days ago · multi-agent, ...            │ │
│    : 23   │   ├─────────────────────────────────────────────────────┤ │
│  Reference│   │ 🤖 Scalable Agent Patterns      [approved] arXiv  │ │
│    : 58   │   │    AI collected · 1 day ago · Score: 92            │ │
│  Auto    │   ├─────────────────────────────────────────────────────┤ │
│    : 42   │   │ 🤖 LLM Agents in Customer Svc  [review] Blog     │ │
│  Manual  │   │    AI collected · 3h ago · Score: 63 ⚠️            │ │
│    : 47   │   └─────────────────────────────────────────────────────┘ │
│          │                                                           │
│  🤖 AI   │   📈 Collector Activity (Today)                           │
│  Collector│   ┌─────────────────────────────────────────────────────┐ │
│  ─────── │   │  Discovered: 47  Evaluated: 45  Approved: 12        │ │
│  Pending │   │  Pending Review: 8  Rejected: 25                    │ │
│  Review: 8│   │  Sources: 🟢5  🟡1  🔴1                            │ │
│          │   └─────────────────────────────────────────────────────┘ │
│  📁 Topics│                                                           │
│  ─────── │   🔥 Trending Topics (This Week)                          │
│  Agent   │   ┌─────────────────────────────────────────────────────┐ │
│  Arch.   │   │  MCP Protocol        ▲ +12 items  🔥               │ │
│  RAG     │   │  Multi-Agent         ▲ +15 items                    │ │
│  Tools   │   │  Agent Memory        ▲ +8 items                     │ │
│  Memory  │   │  Agentic RAG         ▲ +5 items                     │ │
│  ...     │   └─────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────────┘
```

### 8.2. Knowledge Graph View

```
┌──────────────────────────────────────────────────────────────────────┐
│  Filter: [All Types ▼] [All Topics ▼] [All Sources ▼]  🔍 Search   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│         [RAG] ────── [Vector DB]                                     │
│           │    ╲         │                                           │
│           │     ╲        │                                           │
│     [RES-012]   ╲  [RES-008]                                        │
│       │          ╲      │                                            │
│    [arXiv]        ╲     │                                            │
│                    ╲    │                                            │
│      [Embeddings]──[Chunking]     ⚠️ [Agent Security]                │
│           │              │              (GAP - no research)          │
│      [RES-015]      [RES-003]                                       │
│                          │                                           │
│                    [Multi-Agent]                                     │
│                     │        ╲                                       │
│               [RES-001]    [CrewAI]                                  │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│  Legend: 🔵 Research  🟢 Concept  🟡 Tech  🔴 Domain  🟠 Source    │
│          ⚠️ Gap (needs research)                                     │
│  Nodes: 215  Edges: 487  Clusters: 8  Gaps: 3                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.3. Research Item Detail

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← Back                                                             │
│                                                                      │
│  Scalable Multi-Agent Orchestration                                  │
│  Reference · Auto-Approved · RES-2026-042                            │
│  🤖 Collected from arXiv · Jul 8, 2026                              │
│  Authors: Zhang et al.                                               │
│                                                                      │
│  Tags: [multi-agent] [orchestration] [scalability] [patterns]        │
│                                                                      │
│  ┌─ AI Evaluation ───────────────────────────────────────────────┐   │
│  │  Overall: 92/100  ✅ Auto-Approved                            │   │
│  │  Relevance: 95  Quality: 88  Novelty: 90                     │   │
│  │  Actionability: 85  Freshness: 100                            │   │
│  │  Reasoning: "Core topic directly addressing multi-agent       │   │
│  │  orchestration at scale with novel hierarchical approach..."   │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─ Summary (AI-generated) ──────────────────────────────────────┐   │
│  │ Paper proposes a novel hierarchical orchestration framework   │   │
│  │ for scaling multi-agent systems beyond 100 agents...          │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─ Content ─────────────────────────────────────────────────────┐   │
│  │ ## 1. Introduction                                            │   │
│  │ Multi-agent systems at scale face...                          │   │
│  │                                                               │   │
│  │ [📎 Download PDF]  [🔗 View on arXiv]                         │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─ Knowledge Graph (related) ───────────────────────────────────┐   │
│  │        [This] ──extends──→ [RES-003]                          │   │
│  │          │       └──collected_from──→ [arXiv]                  │   │
│  │    [Multi-Agent]         [LangGraph]                           │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─ Related Research ────────────────────────────────────────────┐   │
│  │  📄 Agent Memory Systems (supports)                           │   │
│  │  📄 LangGraph Deep Dive (references)                          │   │
│  │  📄 Single vs Multi-Agent (contradicts)                       │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  [Edit] [Add Comment] [Export PDF] [Re-evaluate] [Archive]          │
└──────────────────────────────────────────────────────────────────────┘
```

### 8.4. Collector Manager Page

```
┌──────────────────────────────────────────────────────────────────────┐
│  🤖 AI Collector Manager                              [+ Add Source] │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─ Review Queue ──────────────────────────────────────────────────┐│
│  │  ⏳ Pending: 8  │  ✅ Auto-Approved: 12  │  ❌ Rejected: 25    ││
│  │  ┌───────────────────────────────────────────────────────────┐  ││
│  │  │ 📄 "LLM Agents in Customer Service" — Medium             │  ││
│  │  │    Score: 63 │ Rel: 78 │ Qual: 55 │ Nov: 50             │  ││
│  │  │    ⚠️ Mostly opinion, limited data                       │  ││
│  │  │    [View] [Approve] [Edit & Approve] [Reject]            │  ││
│  │  ├───────────────────────────────────────────────────────────┤  ││
│  │  │ 📄 "Benchmarking RAG at Scale" — Blog                    │  ││
│  │  │    Score: 58 │ Rel: 70 │ Qual: 60 │ Nov: 45             │  ││
│  │  │    ⚠️ Overlaps with RES-012                              │  ││
│  │  │    [View] [Approve] [Edit & Approve] [Reject]            │  ││
│  │  └───────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─ Source Health ─────────────────────────────────────────────────┐│
│  │  🟢 arXiv          Last: 2h ago  │  15 found  │  3 approved   ││
│  │  🟢 OpenAI Blog    Last: 4h ago  │   2 found  │  1 approved   ││
│  │  🟡 GitHub Trend   Last: 6h ago  │   8 found  │  0 approved   ││
│  │  🔴 HN API         Last: failed  │   —        │  —            ││
│  │  🟢 RSS Feeds      Last: 1h ago  │  22 found  │  8 approved   ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─ Score Distribution (This Week) ────────────────────────────────┐│
│  │  90-100: ██░░░░░░░░  3 items (auto-approved)                    ││
│  │  75-89:  █████░░░░░  9 items (auto-approved)                    ││
│  │  50-74:  ████░░░░░░ 12 items (needs review)                     ││
│  │  25-49:  ████████░░ 28 items (auto-rejected)                    ││
│  │  0-24:   ██████████ 45 items (auto-rejected)                    ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                      │
│  ┌─ Knowledge Gaps Detected ───────────────────────────────────────┐│
│  │  ⚠️ Agent Security Best Practices — 0 items, high demand       ││
│  │     [🤖 Trigger Deep Research]  [Assign to team member]         ││
│  │  ⚠️ Agent Cost Optimization — 1 item, growing interest          ││
│  │     [🤖 Trigger Deep Research]  [Assign to team member]         ││
│  └─────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### 8.5. Training Data Hub

```
┌──────────────────────────────────────────────────────────────────────┐
│  Training Data Hub                         [Build Dataset] [Export]  │
├──────────────────────────────────────────────────────────────────────┤
│  Dataset Health                                                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Examples: 4,820 | Accepted: 2,140 | Needs Review: 312          │  │
│  │ SFT: 1,420 | Tool-calling: 380 | Preference pairs: 340         │  │
│  │ Synthetic: 18% | PII pending: 23 | Holdout leakage: 0          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Review Queue                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ task-456 | sales | lead_qualification | score 0.91 | redacted  │  │
│  │ Labels: correct_tool, actionable, missing_budget_analysis      │  │
│  │ [Trace] [Edit] [Accept] [Eval-only] [Reject]                   │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │ synth-088 | support | escalation_plan | score 0.78 | synthetic │  │
│  │ Source: RES-2026-042, RES-2026-057                             │  │
│  │ [Compare] [Edit] [Accept] [Reject]                             │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Dataset Versions                                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ business-agent-sft-v0.1       train 1,500 / val 200 / test 200 │  │
│  │ tool-calling-v0.2             train   360 / val  60 / test  60 │  │
│  │ business-agent-eval-v0.1      holdout 240                      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Model Eval                                                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ baseline: 72.4 | fine-tuned candidate: 81.6 | safety: no drop   │  │
│  │ Tool correctness +12.5 | Format adherence +9.1 | Cost -6%       │  │
│  │ Decision: needs review before promote                           │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 9. Docker Compose Setup

```yaml
version: "3.9"

services:
  # Frontend + API
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/research
      - NEO4J_URI=bolt://neo4j:7687
      - MEILISEARCH_URL=http://meilisearch:7700
      - OLLAMA_URL=http://ollama:11434
      - REDIS_URL=redis://redis:6379
      - MINIO_URL=http://minio:9000
    depends_on:
      - postgres
      - neo4j
      - meilisearch
      - ollama
      - redis
      - minio

  # PostgreSQL - primary data store
  postgres:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: research
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"

  # Neo4j - knowledge graph
  neo4j:
    image: neo4j:5-community
    volumes:
      - neo4jdata:/data
    environment:
      NEO4J_AUTH: neo4j/password
    ports:
      - "7474:7474"
      - "7687:7687"

  # Meilisearch - search engine
  meilisearch:
    image: getmeili/meilisearch:latest
    volumes:
      - meilidata:/meili_data
    environment:
      MEILI_MASTER_KEY: master_key
    ports:
      - "7700:7700"

  # Ollama - local LLM
  ollama:
    image: ollama/ollama
    volumes:
      - ollamadata:/root/.ollama
    ports:
      - "11434:11434"

  # Redis - task queue
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # MinIO - file storage
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes:
      - miniodata:/data
    environment:
      MINIO_ROOT_USER: minio
      MINIO_ROOT_PASSWORD: minio123
    ports:
      - "9000:9000"
      - "9001:9001"

  # Collector service - AI auto-collection
  collector:
    build: ./services/collector
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/research
      - NEO4J_URI=bolt://neo4j:7687
      - OLLAMA_URL=http://ollama:11434
      - REDIS_URL=redis://redis:6379
      - BROWSERLESS_URL=ws://browserless:3333
      - MINIO_URL=http://minio:9000
    depends_on:
      - postgres
      - neo4j
      - redis
      - ollama
      - browserless
    volumes:
      - collector_data:/app/data  # downloaded PDFs, cached content

  # Training data worker - redaction, example conversion, dataset export, eval
  training-worker:
    build: ./services/training
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/research
      - REDIS_URL=redis://redis:6379
      - OLLAMA_URL=http://ollama:11434
      - MINIO_URL=http://minio:9000
      - DATASET_BUCKET=training-datasets
    depends_on:
      - postgres
      - redis
      - ollama
      - minio
    volumes:
      - training_data:/app/data  # JSONL/Parquet exports, eval reports

  # Optional labeling UI for larger review workflows
  label-studio:
    image: heartexlabs/label-studio:latest
    ports:
      - "8080:8080"
    volumes:
      - labelstudio_data:/label-studio/data
    profiles:
      - labeling

  # Browserless - headless Chrome for web scraping
  browserless:
    image: browserless/chrome:latest
    environment:
      MAX_CONCURRENT_SESSIONS: 5
      CONNECTION_TIMEOUT: 120000
    ports:
      - "3333:3333"

volumes:
  pgdata:
  neo4jdata:
  meilidata:
  ollamadata:
  miniodata:
  collector_data:
  training_data:
  labelstudio_data:
```

---

## 10. Implementation Roadmap

### Phase 1: Foundation (2-3 tuần)
- [ ] Setup project structure (Next.js + FastAPI + Docker Compose)
- [ ] PostgreSQL schema + migrations (including collector + training data tables)
- [ ] CRUD API cho research items
- [ ] Basic UI: list view, detail view, create/edit form
- [ ] Markdown editor integration
- [ ] Authentication (basic login)

### Phase 2: Knowledge Graph (2-3 tuần)
- [ ] Neo4j setup + graph model (including CollectorSource, ResearchGap nodes)
- [ ] Sync pipeline: PostgreSQL → Neo4j
- [ ] Graph visualization component (Cytoscape.js)
- [ ] Interactive features: filter, zoom, highlight paths
- [ ] Manual relation management UI
- [ ] Gap visualization trong graph

### Phase 3: Search & AI (2 tuần)
- [ ] Meilisearch integration + indexing
- [ ] Ollama setup + model selection
- [ ] Auto-tagging pipeline
- [ ] Auto-summarization
- [ ] Semantic search với embeddings
- [ ] Concept extraction
- [ ] Deduplication (fingerprint + semantic)

### Phase 4: AI Auto-Collector (3-4 tuần)
- [ ] BaseCollector framework + plugin system
- [ ] ArxivCollector (API integration + PDF download)
- [ ] RSSCollector (feed parsing)
- [ ] GitHubCollector (API integration)
- [ ] WebScraperCollector (Playwright + Browserless)
- [ ] Scheduler (APScheduler + cron jobs)
- [ ] AI Evaluation Pipeline (relevance, quality, novelty, actionability, freshness scoring)
- [ ] Content extraction (PDF → Markdown, HTML → clean text)
- [ ] Auto-enrichment (summarize, extract concepts, find relations)
- [ ] Graph ingestion (add approved items to PostgreSQL + Neo4j)
- [ ] Review queue API + UI
- [ ] Source management UI
- [ ] Collector dashboard (stats, health, monitoring)

### Phase 5: Training Data Hub (2-3 tuần)
- [ ] Training event ingestion API từ Business AI Agent runtime
- [ ] PII redaction + policy check pipeline
- [ ] Training examples review queue
- [ ] Dataset builder + dataset versioning
- [ ] JSONL/Parquet export for SFT/tool-calling/preference datasets
- [ ] Eval set management + model eval dashboard
- [ ] Synthetic example generation từ approved research/SOP

### Phase 6: Collaboration & Polish (2 tuần)
- [ ] Review workflow (draft → review → approved cho manual items)
- [ ] Collector review workflow (approve/reject/edit auto-collected items)
- [ ] Comments system
- [ ] Version history
- [ ] Dashboard + analytics (including collector stats)
- [ ] Activity feed (manual + auto-collected)
- [ ] Weekly digest emails

### Phase 7: Intelligence Layer (ongoing)
- [ ] Research Agent (deep research on topics)
- [ ] Auto gap detection + filling
- [ ] Feedback learning (AI cải thiện scoring từ human reviews)
- [ ] Fine-tune feedback loop từ eval failures và human corrections
- [ ] Model promotion gate dựa trên eval metrics
- [ ] Trend detection & prediction
- [ ] Q&A chatbot over knowledge base (RAG)
- [ ] Cross-source synthesis reports
- [ ] Personalized recommendations per team member
- [ ] Podcast/video transcription + ingestion
- [ ] Citation graph analysis
- [ ] Export reports
- [ ] Mobile responsive improvements
- [ ] Performance optimization

---

## 11. Lightweight Alternative: Obsidian-Based

Nếu muốn bắt đầu ngay trong 30 phút mà chưa cần build app:

### Setup
1. Tạo Obsidian vault chung cho team
2. Sync qua Git (mỗi người clone, commit khi thêm/sửa)
3. Cấu trúc thư mục:

```
research-vault/
├── internal-research/
│   ├── 2026-07-01-multi-agent-orchestration.md
│   └── 2026-07-03-rag-benchmark.md
├── references/
│   ├── 2026-06-28-arxiv-agent-memory.md
│   └── 2026-07-02-langchain-docs-tools.md
├── concepts/
│   ├── multi-agent.md
│   ├── rag.md
│   └── function-calling.md
├── technologies/
│   ├── langchain.md
│   └── crewai.md
├── training-data/
│   ├── examples/
│   │   ├── sft/
│   │   ├── tool-calling/
│   │   └── preference/
│   ├── evals/
│   └── datasets/
└── templates/
    ├── internal-research.md
    ├── reference.md
    ├── training-example.md
    └── eval-case.md
```

### Markdown template

```markdown
---
type: internal-research
status: draft
authors: [Linh, Minh]
tags: [multi-agent, orchestration]
related: [agent-memory, langgraph]
created: 2026-07-01
---

# Multi-Agent Orchestration Patterns

## Summary
...

## Content
...

## References
- [[2026-06-28-arxiv-agent-memory]]
- [[multi-agent]]
- [[langchain]]
```

### Training example template

```markdown
---
type: training-example
example_type: instruction-sft
status: candidate
business_domain: sales
task_type: lead_qualification
source: human-correction
pii_status: redacted
dataset_split: train
labels: [actionable, correct_tool, good_tone]
related_research: [RES-2026-042]
---

# Lead Qualification Example

## Instruction
...

## Context
...

## Expected Response
...

## Review Notes
...
```

### Ưu điểm
- Zero cost, setup 30 phút
- Obsidian Graph View hiển thị knowledge graph tự động
- Markdown-native, Git-friendly
- Plugins: Dataview (query), Templater, Kanban

### Nhược điểm
- Không có semantic search
- Không có AI features (trừ khi cài thêm plugin)
- Training data chỉ phù hợp để thử workflow nhỏ; thiếu PII redaction, dataset versioning và eval automation
- Collaboration qua Git không thuận tiện cho non-devs
- Không có dashboard/analytics
- Graph visualization cơ bản, khó customize

---

## 12. Decision Matrix

| Tiêu chí | Custom App (Full) | Custom App (Lightweight) | Obsidian + Git |
|---|---|---|---|
| Setup time | 12-15 tuần | 8-10 tuần | 30 phút |
| Knowledge Graph | ★★★ Customizable, interactive | ★★ pg_graph, basic | ★★ Basic but functional |
| Search | ★★★ Full-text + semantic | ★★ PG full-text + pgvector | ★★ Full-text only |
| AI Features | ★★★ Auto-tag, summarize, Q&A | ★★★ Same | ★ Plugin-dependent |
| Auto-Collector | ★★★ Multi-source, AI scoring, review queue | ★★ Fewer sources, basic scoring | ✗ Manual only |
| Training Data Hub | ★★★ Event capture, review, dataset versioning, eval | ★★ Basic examples + export | ★ Manual Markdown only |
| PII/Policy Controls | ★★★ Redaction, provenance, split integrity | ★★ Basic redaction pipeline | ✗ Manual discipline |
| Model Eval Loop | ★★★ Eval dashboard + promotion gates | ★★ Scripted evals | ✗ Manual |
| Deduplication | ★★★ 3-layer (URL + fingerprint + semantic) | ★★ 2-layer (URL + semantic) | ✗ Manual |
| Collaboration | ★★★ Real-time, roles, review workflow | ★★ Basic | ★ Git-based |
| Maintenance | ★ Needs DevOps (8 containers) | ★★ Moderate (3-4 containers) | ★★★ Almost none |
| Scalability | ★★★ Good | ★★ Moderate | ★ Limited |
| Cost | ~$80-150/mo server | ~$40-80/mo server | Free |
| Customization | ★★★ Unlimited | ★★★ Unlimited | ★★ Plugin-dependent |

**Recommendation**:
- **Team < 3 người, chưa có thói quen research**: Bắt đầu với Obsidian để validate workflow, sau đó migrate lên Custom App
- **Team 3-5 người, đã biết cần gì**: Build Custom App Lightweight trước, upgrade dần
- **Team > 5 người, cần auto-collection**: Build Custom App Full từ đầu

---

## 13. AI Auto-Collector: Tự động thu thập & đánh giá tài liệu

> Hệ thống AI agents tự động đi thu thập tài liệu từ nhiều nguồn, đánh giá mức độ phù hợp, download nội dung, xử lý và tự động thêm vào Knowledge Graph. Human-in-the-loop chỉ can thiệp khi phát hiện knowledge gap lớn.

### 13.1. Tổng quan Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AI AUTO-COLLECTOR PIPELINE                       │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ 1.DISCOVER│──▶│2.EXTRACT │──▶│3.EVALUATE│──▶│4.PROCESS │        │
│  │  (Crawl)  │   │ (Parse)  │   │ (Score)  │   │(Enrich)  │        │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘        │
│       │              │              │              │                 │
│       ▼              ▼              ▼              ▼                 │
│  Nguồn: arXiv    Content:       Score: 0-100    Auto:              │
│  GitHub, Blogs   title,         Relevance       - summarize        │
│  RSS, Twitter    abstract,      Quality         - extract          │
│  Conferences     full text,     Novelty           concepts         │
│  Newsletters     metadata       Freshness       - find relations   │
│                                  Duplication     - generate tags    │
│                                                     │               │
│                                                     ▼               │
│                                              ┌──────────┐           │
│                                              │5.INGEST  │           │
│                                              │(Auto-add │           │
│                                              │ to Graph)│           │
│                                              └──────────┘           │
│                                                     │               │
│                                                     ▼               │
│                                              ┌──────────┐           │
│                                              │6.GAP     │           │
│                                              │DETECTION │           │
│                                              │(if gap → │           │
│                                              │ human)   │           │
│                                              └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘

Logic:
- Tài liệu AI thu thập → auto-ingest vào graph (badge "🤖 AI-collected")
- Tài liệu người thu thập → manual workflow (badge "👤 Human-collected")
- Human-in-the-loop CHỈ khi: phát hiện knowledge gap lớn
  → AI đề xuất team member research HOẶC AI tự deep research (có human review)
```

### 13.2. Nguồn thu thập (Sources)

#### Tier 1: Academic & Technical (Ưu tiên cao)

| Nguồn | Phương thức | Tần suất | Nội dung |
|---|---|---|---|
| **arXiv** | API (`arxiv.org/api`) | Hàng ngày | Papers: AI agents, LLM, multi-agent, RAG |
| **Semantic Scholar** | API | Hàng ngày | Papers + citations graph |
| **Papers With Code** | RSS + Scraping | Hàng ngày | Papers kèm code implementation |
| **DBLP** | API | Hàng tuần | Computer science publications |
| **ACL Anthology** | Scraping | Hàng tuần | NLP/LLM papers |

#### Tier 2: Industry & Engineering Blogs

| Nguồn | Phương thức | Tần suất | Nội dung |
|---|---|---|---|
| **OpenAI Blog** | RSS feed | Hàng ngày | Research announcements, best practices |
| **Anthropic Blog** | RSS feed | Hàng ngày | Claude research, safety, alignment |
| **Google AI Blog** | RSS feed | Hàng ngày | DeepMind, Gemini research |
| **LangChain Blog** | RSS feed | Hàng ngày | Framework updates, patterns |
| **LlamaIndex Blog** | RSS feed | Hàng ngày | RAG, data agents |
| **Microsoft Research** | RSS feed | Hàng tuần | AutoGen, Semantic Kernel |
| **HuggingFace Blog** | RSS feed | Hàng tuần | Open-source models, tools |
| **CrewAI Blog** | RSS feed | Hàng tuần | Multi-agent patterns |

#### Tier 3: Community & Practitioner

| Nguồn | Phương thức | Tần suất | Nội dung |
|---|---|---|---|
| **GitHub Trending** | API + Scraping | Hàng ngày | Repos: agents, LLM apps, frameworks |
| **Hacker News** | API (Algolia) | Hàng ngày | Discussions về AI agents |
| **Reddit** | API (r/MachineLearning, r/LocalLLaMA, r/LangChain) | Hàng ngày | Community insights |
| **Dev.to / Medium** | RSS + API | Hàng tuần | Tutorials,实践经验 |
| **Substack newsletters** | RSS (The Batch, TLDR AI, AI Engineer) | Hàng ngày | Curated content |

#### Tier 4: Business & Enterprise

| Nguồn | Phương thức | Tần suất | Nội dung |
|---|---|---|---|
| **McKinsey / BCG / Deloitte** | Scraping | Hàng tuần | AI in business reports |
| **Gartner / Forrester** | Scraping | Hàng tháng | Industry analysis |
| **Case study sites** | Scraping | Hàng tuần | Enterprise AI deployments |
| **Product Hunt** | API | Hàng tuần | New AI agent products |

#### Tier 5: Social & Real-time

| Nguồn | Phương thức | Tần suất | Nội dung |
|---|---|---|---|
| **X/Twitter** | API (filtered) | Hàng ngày | AI researchers, announcements |
| **YouTube** | API | Hàng tuần | Conference talks, tutorials |
| **Podcast transcripts** | RSS + Whisper | Hàng tuần | AI podcasts → text |

### 13.3. Cấu hình nguồn thu thập (Source Configuration)

```yaml
# collector-config.yaml
sources:
  - name: arxiv
    type: api
    enabled: true
    schedule: "0 6 * * *"  # 6AM daily
    config:
      base_url: "http://export.arxiv.org/api/query"
      queries:
        - 'cat:cs.AI AND all:"agent"'
        - 'cat:cs.CL AND all:"multi-agent"'
        - 'all:"retrieval augmented generation"'
        - 'all:"LLM agent" AND all:"tool use"'
        - 'all:"function calling" AND all:"language model"'
      max_results_per_query: 50
      sort_by: submittedDate
    filters:
      min_date: "2024-01-01"
      languages: ["en"]

  - name: openai_blog
    type: rss
    enabled: true
    schedule: "0 */6 * * *"  # every 6 hours
    config:
      feed_url: "https://openai.com/blog/rss.xml"
    filters:
      keywords_include: ["agent", "tool", "function", "multi-agent", "reasoning"]

  - name: github_trending
    type: scraper
    enabled: true
    schedule: "0 8 * * *"  # 8AM daily
    config:
      url: "https://github.com/trending/python"
      topics: ["agent", "llm", "rag", "multi-agent", "langchain", "crewai"]
      min_stars: 100
      min_stars_last_week: 10

  - name: hacker_news
    type: api
    enabled: true
    schedule: "0 */4 * * *"  # every 4 hours
    config:
      base_url: "https://hn.algolia.com/api/v1"
      queries:
        - "AI agent"
        - "multi-agent system"
        - "LLM agent"
        - "agentic workflow"
      min_points: 20
      min_comments: 5

  - name: twitter_ai_researchers
    type: api
    enabled: true
    schedule: "0 */2 * * *"  # every 2 hours
    config:
      accounts:
        - "kaboroevich"     # Andrew Karlov
        - "swyx"            # Swyx (AI Engineer)
        - "LangChainAI"
        - "AndrewYNg"
        - "jxnlco"          # Jason Liu
      keywords: ["agent", "multi-agent", "tool use", "agentic"]
```

### 13.4. Phase 1: DISCOVER — Thu thập raw items

Mỗi source có một **Collector Agent** riêng:

```python
# Pseudo-code cho Collector Agent architecture

class BaseCollector:
    """Base class cho tất cả collectors"""

    async def discover(self) -> list[RawItem]:
        """Tìm các items mới từ source"""
        pass

    async def extract(self, raw: RawItem) -> ExtractedItem:
        """Parse và extract nội dung đầy đủ"""
        pass


class ArxivCollector(BaseCollector):
    """Thu thập papers từ arXiv API"""

    async def discover(self) -> list[RawItem]:
        # Query arXiv API với configured search terms
        # Filter theo date (chỉ lấy papers mới từ lần chạy trước)
        # Return list of RawItem(arxiv_id, title, abstract, authors, pdf_url)
        pass

    async def extract(self, raw: RawItem) -> ExtractedItem:
        # Download PDF
        # Parse PDF → text (dùng marker, PyMuPDF, hoặc Nougat cho OCR)
        # Extract: title, abstract, sections, references, figures
        pass


class RSSCollector(BaseCollector):
    """Thu thập từ RSS feeds (blogs, newsletters)"""

    async def discover(self) -> list[RawItem]:
        # Parse RSS feed
        # Filter items mới (chưa thấy trước đó)
        pass

    async def extract(self, raw: RawItem) -> ExtractedItem:
        # Fetch full article URL
        # Dùng readability / trafilatura để extract main content
        # Strip ads, nav, footers
        pass


class GitHubCollector(BaseCollector):
    """Thu thập trending repos"""

    async def discover(self) -> list[RawItem]:
        # Query GitHub trending / search API
        # Filter repos liên quan tới AI agents
        pass

    async def extract(self, raw: RawItem) -> ExtractedItem:
        # Fetch README
        # Fetch repo metadata (stars, forks, topics, last commit)
        # Optionally: fetch key source files (agent.py, main.py)
        pass


class WebScraperCollector(BaseCollector):
    """Generic web scraper cho các trang không có API/RSS"""

    async def discover(self) -> list[RawItem]:
        # Crawl configured URLs
        # Extract links từ listing pages
        pass

    async def extract(self, raw: RawItem) -> ExtractedItem:
        # Fetch page, extract content
        # Handle different page templates per site
        pass
```

### 13.5. Phase 2: EXTRACT — Xử lý nội dung

```python
class ContentExtractor:
    """Extract structured content từ raw items"""

    def extract_from_pdf(self, pdf_bytes: bytes) -> ExtractedContent:
        """
        Dùng cho arXiv papers, reports
        Pipeline:
        1. PDF → Markdown (dùng Marker hoặc Nougat)
        2. Extract sections: abstract, intro, methods, results, conclusion
        3. Extract references (citation links)
        4. Extract figures/tables captions
        """
        pass

    def extract_from_html(self, url: str, html: str) -> ExtractedContent:
        """
        Dùng cho blog posts, articles
        Pipeline:
        1. readability-lxml → main content
        2. trafilatura → clean text + metadata
        3. Extract code blocks, images
        """
        pass

    def extract_from_github(self, repo_url: str) -> ExtractedContent:
        """
        Dùng cho GitHub repos
        Pipeline:
        1. Fetch README.md
        2. Fetch repo metadata (description, topics, stars)
        3. Optionally: analyze key source files
        """
        pass


class ExtractedContent:
    title: str
    authors: list[str]
    published_date: datetime
    abstract: str | None          # 2-3 câu tóm tắt
    full_text: str                # Nội dung đầy đủ
    sections: dict[str, str]      # {"introduction": "...", "methods": "..."}
    references: list[str]         # URLs hoặc citation strings
    code_blocks: list[str]        # Code snippets nếu có
    images: list[ImageRef]        # Hình ảnh nếu có
    metadata: dict                # Source-specific metadata
    source_url: str
    source_type: str              # "arxiv", "blog", "github", etc.
    raw_file_path: str | None     # Path tới file gốc (PDF, etc.)
```

### 13.6. Phase 3: EVALUATE — AI đánh giá mức độ phù hợp

Đây là phase quan trọng nhất — dùng LLM để đánh giá mỗi extracted item.

#### Relevance Scoring Model

```python
class RelevanceEvaluator:
    """
    Đánh giá mỗi tài liệu trên nhiều tiêu chí.
    Output: overall_score (0-100) + breakdown + recommendation.
    """

    async def evaluate(self, item: ExtractedContent) -> EvaluationResult:
        # Chạy song song các evaluators
        scores = await asyncio.gather(
            self.score_relevance(item),      # Mức độ liên quan tới AI Agents for Business
            self.score_quality(item),         # Chất lượng nội dung
            self.score_novelty(item),         # Độ mới so với knowledge base hiện tại
            self.score_actionability(item),   # Có thể áp dụng thực tế không
            self.score_freshness(item),       # Độ mới về thời gian
            self.check_duplicate(item),       # Có trùng với items đã có không
        )
        return self.aggregate(scores)
```

#### Chi tiết từng Score

```python
# 1. RELEVANCE SCORE (0-100) — Trọng số: 35%
# Hỏi LLM: "Tài liệu này liên quan thế nào tới AI Agents for Business?"

RELEVANCE_PROMPT = """
You are evaluating a research document for relevance to our team's focus:
"AI Agents for Business" — building, deploying, and managing AI agent systems
for business applications.

Our key research areas:
{research_areas_from_config}

Existing knowledge graph topics:
{top_concepts_from_graph}

Document:
Title: {title}
Abstract: {abstract}
Content preview: {content_preview}

Rate relevance from 0-100 and explain:
- 90-100: Core topic, directly about AI agents for business
- 70-89: Highly related, covers key enabling technology
- 50-69: Somewhat related, has applicable insights
- 30-49: Tangentially related
- 0-29: Not relevant

Output JSON: {"score": int, "reasoning": str, "matched_topics": [str]}
"""


# 2. QUALITY SCORE (0-100) — Trọng số: 20%
# Đánh giá chất lượng nội dung

QUALITY_PROMPT = """
Evaluate the quality of this research document:

Title: {title}
Content: {content_preview}
Source: {source_type} ({source_name})

Rate quality from 0-100 based on:
- Depth of analysis (surface-level vs deep dive)
- Evidence quality (claims backed by data/experiments vs opinions)
- Writing clarity and structure
- Technical accuracy
- For papers: methodology rigor, reproducibility
- For blog posts: practical value, code examples
- For repos: documentation quality, activity level, community adoption

Output JSON: {"score": int, "reasoning": str, "quality_signals": [str]}
"""


# 3. NOVELTY SCORE (0-100) — Trọng số: 20%
# So sánh với knowledge base hiện tại

async def score_novelty(self, item: ExtractedContent) -> Score:
    # 1. Embedding similarity với tất cả items hiện có
    item_embedding = await self.embed(item.abstract + item.full_text[:2000])
    similar_items = await self.vector_db.similarity_search(
        item_embedding, top_k=5
    )

    # 2. Nếu similarity cao (>0.9) → low novelty
    # 3. Nếu similarity thấp (<0.5) → high novelty
    # 4. LLM check: "Tài liệu này mang lại gì mới so với các tài liệu sau?"

    NOVELTY_PROMPT = """
    We already have these related documents in our knowledge base:
    {similar_items_summaries}

    New document:
    Title: {title}
    Abstract: {abstract}

    How novel is this new document compared to what we already have?
    - 90-100: Completely new topic or groundbreaking approach
    - 70-89: Significant new insights on existing topic
    - 50-69: Moderate new information, extends existing knowledge
    - 30-49: Mostly overlaps with existing knowledge
    - 0-29: Redundant, no new information

    Output JSON: {"score": int, "reasoning": str, "overlaps_with": [str]}
    """


# 4. ACTIONABILITY SCORE (0-100) — Trọng số: 15%
# Có thể áp dụng vào thực tế không?

ACTIONABILITY_PROMPT = """
Evaluate how actionable this document is for a team building AI agents:

Title: {title}
Content preview: {content_preview}

Rate actionability 0-100:
- 90-100: Ready-to-use patterns, code, frameworks we can adopt immediately
- 70-89: Clear implementation guidance with examples
- 50-69: Useful concepts but needs adaptation
- 30-49: Mostly theoretical, limited practical application
- 0-29: Purely theoretical or abstract

Output JSON: {"score": int, "reasoning": str, "actionable_items": [str]}
"""


# 5. FRESHNESS SCORE (0-100) — Trọng số: 10%
# Dựa trên thời gian xuất bản

def score_freshness(self, item: ExtractedContent) -> Score:
    days_old = (now() - item.published_date).days
    if days_old <= 7:    return 100  # This week
    if days_old <= 30:   return 85   # This month
    if days_old <= 90:   return 70   # This quarter
    if days_old <= 180:  return 55   # Last 6 months
    if days_old <= 365:  return 40   # This year
    return 20                         # Older than 1 year
```

#### Aggregate & Recommendation

```python
class EvaluationResult:
    overall_score: float          # Weighted average
    relevance_score: float        # 35%
    quality_score: float          # 20%
    novelty_score: float          # 20%
    actionability_score: float    # 15%
    freshness_score: float        # 10%
    is_duplicate: bool
    duplicate_of: str | None      # ID of duplicate item
    action: str                   # "ingest" | "skip"
    reasoning: str                # LLM's overall reasoning
    suggested_tags: list[str]     # AI-suggested tags
    suggested_relations: list     # AI-suggested relations to existing items
    suggested_concepts: list[str] # New concepts to add to graph
    fills_gap: str | None         # Gap topic this item helps fill (if any)


def aggregate(self, scores: list[Score]) -> EvaluationResult:
    weights = {
        "relevance": 0.35,
        "quality": 0.20,
        "novelty": 0.20,
        "actionability": 0.15,
        "freshness": 0.10,
    }

    overall = sum(s.score * weights[s.name] for s in scores)

    # Decision logic: auto-ingest tất cả, chỉ skip duplicates
    if result.is_duplicate:
        action = "skip"           # Skip duplicates
    else:
        action = "ingest"         # Auto-ingest vào Knowledge Graph, không cần human review

    # Check if this item fills a knowledge gap
    gap = await self.gap_detector.check_if_fills_gap(result.suggested_concepts)

    return EvaluationResult(overall_score=overall, action=action, fills_gap=gap, ...)
```

**Lưu ý quan trọng:**
- **Không có review queue cho từng item** — AI thu thập xong tự động thêm vào graph
- **Phân loại rõ ràng** trong database: `collection_method = 'auto-collected'`
- **UI hiển thị khác biệt**: badge "🤖 AI" cho auto-collected items, badge "👤 Human" cho manual items
- **Human chỉ can thiệp khi**: phát hiện knowledge gap lớn → đề xuất research hoặc AI deep research

### 13.7. Phase 4: PROCESS — Enrichment & Auto-tagging

```python
class ItemProcessor:
    """Enrich approved items trước khi thêm vào graph"""

    async def process(self, item: ExtractedContent, eval: EvaluationResult) -> ProcessedItem:
        # 1. Generate summary (nếu chưa có)
        summary = await self.llm_summarize(item.full_text)

        # 2. Extract concepts/topics
        concepts = await self.extract_concepts(item.full_text)

        # 3. Extract technologies mentioned
        technologies = await self.extract_technologies(item.full_text)

        # 4. Extract business domains applicable
        domains = await self.extract_domains(item.full_text)

        # 5. Find relations to existing items
        relations = await self.find_relations(item)

        # 6. Generate embedding cho semantic search
        embedding = await self.embed(item.full_text)

        # 7. Download & store attachments
        file_path = await self.store_file(item)

        return ProcessedItem(
            title=item.title,
            type="reference",
            status="auto-approved" if eval.recommendation == "approve" else "pending-review",
            summary=summary,
            content=item.full_text,
            source_url=item.source_url,
            tags=eval.suggested_tags,
            concepts=concepts,
            technologies=technologies,
            domains=domains,
            relations=relations,
            embedding=embedding,
            evaluation=eval,
            attachments=[file_path] if file_path else [],
        )

    async def extract_concepts(self, text: str) -> list[Concept]:
        """Dùng LLM extract concepts + match với existing concepts trong graph"""
        CONCEPT_PROMPT = """
        Extract key AI/agent concepts from this text.
        Existing concepts in our knowledge graph: {existing_concepts}

        For each concept found:
        - If it matches an existing concept, return the existing name
        - If it's new, suggest a name and description

        Text: {text_preview}
        Output JSON: {"concepts": [{"name": str, "is_new": bool, "description": str}]}
        """

    async def find_relations(self, item: ExtractedContent) -> list[Relation]:
        """Tìm quan hệ giữa item mới và các items hiện có"""
        # 1. Semantic similarity search → top 10 related items
        # 2. Citation analysis: item này cite items nào trong KB?
        # 3. LLM: "Tài liệu này có quan hệ gì với các tài liệu sau?"

        RELATION_PROMPT = """
        New document: {title} - {abstract}

        Potentially related documents in our knowledge base:
        {related_items_list}

        For each related document, determine the relationship type:
        - references: cites or mentions it
        - extends: builds upon its work
        - contradicts: disagrees with its findings
        - supports: confirms or validates its approach
        - depends-on: requires its results/methods
        - inspired-by: was influenced by it

        Output JSON: {"relations": [{"target_title": str, "type": str, "reasoning": str}]}
        """
```

### 13.8. Phase 5: GAP DETECTION — Human-in-the-Loop (chỉ khi cần)

**Logic mới:**
- **AI-collected items**: tự động ingest vào Knowledge Graph, không cần human review
- **Human chỉ can thiệp khi**: AI phát hiện knowledge gap lớn → đề xuất research hoặc tự deep research

```
┌─────────────────────────────────────────────────────────────────────┐
│                  KNOWLEDGE GAP DETECTION UI                           │
│                                                                     │
│  ┌─ Gaps Detected ─────────────────────────────────────────────────┐│
│  │  ⚠️ Agent Security Best Practices                              ││
│  │     Severity: HIGH │ Related items: 0 │ Demand: growing        ││
│  │     AI suggests: Deep research on security patterns             ││
│  │     [🤖 AI Deep Research]  [👤 Assign to Team]  [Ignore]      ││
│  │                                                                 ││
│  │  ⚠️ Agent Cost Optimization                                    ││
│  │     Severity: MEDIUM │ Related items: 1 │ Demand: stable       ││
│  │     AI suggests: Collect more resources on cost management      ││
│  │     [🤖 AI Deep Research]  [👤 Assign to Team]  [Ignore]      ││
│  │                                                                 ││
│  │  ⚠️ Production Deployment Patterns                             ││
│  │     Severity: HIGH │ Related items: 2 │ Demand: high           ││
│  │     AI suggests: Research real-world deployment case studies    ││
│  │     [🤖 AI Deep Research]  [👤 Assign to Team]  [Ignore]      ││
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                     │
│  ┌─ AI Deep Research Queue ────────────────────────────────────────┐│
│  │  🔄 "Agent Security Patterns" — In Progress                    ││
│  │     Started: 2h ago │ Sources scanned: 8/15                    ││
│  │     [View Progress]  [Cancel]                                  ││
│  │                                                                 ││
│  │  ✅ "Multi-Agent Communication" — Completed (awaiting review)  ││
│  │     Items found: 12 │ Report generated                         ││
│  │     [Review Report]  [Approve & Publish]  [Request Changes]    ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

#### Gap Detection Logic

```python
class GapDetector:
    """Phát hiện knowledge gaps trong graph"""

    async def detect_gaps(self) -> list[KnowledgeGap]:
        gaps = []

        # 1. Analyze topic clusters — tìm topics có ít research
        clusters = await self.graph.get_topic_clusters()
        for cluster in clusters:
            if cluster.item_count < 3 and cluster.importance > 0.7:
                gaps.append(KnowledgeGap(
                    topic=cluster.name,
                    severity="HIGH" if cluster.importance > 0.8 else "MEDIUM",
                    related_items=cluster.item_count,
                    reason="Important topic with insufficient coverage"
                ))

        # 2. Analyze trending topics từ collector data
        trending = await self.collector.get_trending_topics(days=7)
        for topic in trending:
            existing = await self.graph.count_items_for_topic(topic.name)
            if existing < 2 and topic.mentions > 10:
                gaps.append(KnowledgeGap(
                    topic=topic.name,
                    severity="MEDIUM",
                    related_items=existing,
                    reason=f"Trending topic ({topic.mentions} mentions) with limited research"
                ))

        # 3. Analyze concept connections — tìm missing links
        isolated_concepts = await self.graph.get_isolated_concepts(min_connections=0)
        for concept in isolated_concepts:
            if concept.mentions_in_items > 5:
                gaps.append(KnowledgeGap(
                    topic=concept.name,
                    severity="LOW",
                    related_items=concept.mentions_in_items,
                    reason="Concept mentioned frequently but not well-connected"
                ))

        return sorted(gaps, key=lambda g: g.severity, reverse=True)
```

#### Gap-Based Actions

| Action | Mô tả | Khi nào dùng |
|---|---|---|
| **🤖 AI Deep Research** | AI tự động research sâu về gap topic, tạo comprehensive report | Gap phức tạp, cần tổng hợp từ nhiều nguồn |
| **👤 Assign to Team** | Giao cho team member research và viết internal research | Gap cần expertise cụ thể hoặc practical insights |
| **Ignore** | Bỏ qua gap này (có thể revisit sau) | Gap không quan trọng hoặc đã có đủ info |

**Lưu ý:**
- AI-collected items thông thường → **auto-ingest**, không qua review
- Chỉ khi AI tạo **deep research report** để fill gap → human review report trước khi publish
- Human-collected items (manual) → vẫn có review workflow riêng (draft → review → approved)

### 13.9. Phase 6: INGEST — Thêm vào Knowledge Graph

```python
class GraphIngester:
    """Auto-ingest items vào Knowledge Graph (không cần human approval)"""

    async def ingest(self, item: ProcessedItem):
        # 1. Insert vào PostgreSQL với collection_method = 'auto-collected'
        research_id = await self.db.insert_research_item({
            **item.dict(),
            "collection_method": "auto-collected",
            "status": "approved",  # auto-approved, không cần review
        })

        # 2. Insert/update concepts trong Neo4j
        for concept in item.concepts:
            if concept.is_new:
                await self.neo4j.create_concept(concept)
            await self.neo4j.link_research_to_concept(research_id, concept.name)

        # 3. Insert/update technologies
        for tech in item.technologies:
            await self.neo4j.ensure_technology(tech)
            await self.neo4j.link_uses_tech(research_id, tech)

        # 4. Insert/update business domains
        for domain in item.domains:
            await self.neo4j.ensure_domain(domain)
            await self.neo4j.link_applies_to(research_id, domain)

        # 5. Create relations
        for relation in item.relations:
            target_id = await self.db.find_by_title(relation.target_title)
            if target_id:
                await self.db.insert_relation(research_id, target_id, relation.type)
                await self.neo4j.create_relation(research_id, target_id, relation.type)

        # 6. Index trong Meilisearch
        await self.search_engine.index(research_id, item)

        # 7. Store embedding
        await self.vector_db.upsert(research_id, item.embedding)

        # 8. Store attachments trong MinIO
        for attachment in item.attachments:
            await self.object_storage.upload(attachment)

        # 9. Notify team
        await self.notify(f"New research added: {item.title}")
```

### 13.10. Database Schema bổ sung

```sql
-- Collector sources configuration
CREATE TABLE collector_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,           -- "arxiv", "openai_blog", etc.
    type VARCHAR(20) NOT NULL,           -- "api", "rss", "scraper"
    enabled BOOLEAN DEFAULT true,
    schedule TEXT,                        -- cron expression
    config JSONB NOT NULL DEFAULT '{}',  -- source-specific config
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(20),         -- "success", "error", "partial"
    last_run_items_found INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Raw discovered items (before evaluation)
CREATE TABLE collector_raw_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES collector_sources(id),
    external_id TEXT NOT NULL,           -- arxiv ID, URL, etc.
    title TEXT,
    url TEXT,
    raw_data JSONB,                      -- raw extracted data
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, external_id)       -- prevent duplicates at source level
);

-- Evaluation results
CREATE TABLE collector_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_item_id UUID REFERENCES collector_raw_items(id) ON DELETE CASCADE,
    overall_score FLOAT NOT NULL,
    relevance_score FLOAT,
    quality_score FLOAT,
    novelty_score FLOAT,
    actionability_score FLOAT,
    freshness_score FLOAT,
    is_duplicate BOOLEAN DEFAULT false,
    duplicate_of UUID REFERENCES research_items(id),
    recommendation VARCHAR(20) NOT NULL,  -- "approve", "review", "reject"
    reasoning TEXT,
    suggested_tags TEXT[],
    suggested_relations JSONB,
    suggested_concepts JSONB,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    evaluated_by VARCHAR(20) DEFAULT 'ai' -- 'ai' or user_id
);

-- Review queue
CREATE TABLE collector_review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_item_id UUID REFERENCES collector_raw_items(id) ON DELETE CASCADE,
    evaluation_id UUID REFERENCES collector_evaluations(id),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, snoozed
    assigned_to UUID REFERENCES users(id),
    reviewed_by UUID REFERENCES users(id),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    snooze_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Collector run history
CREATE TABLE collector_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES collector_sources(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status VARCHAR(20),                   -- running, success, error, partial
    items_discovered INT DEFAULT 0,
    items_evaluated INT DEFAULT 0,
    items_approved INT DEFAULT 0,
    items_rejected INT DEFAULT 0,
    items_needing_review INT DEFAULT 0,
    error_message TEXT
);

-- Deduplication fingerprints
CREATE TABLE content_fingerprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    research_item_id UUID REFERENCES research_items(id) ON DELETE CASCADE,
    fingerprint TEXT NOT NULL,            -- MinHash hoặc simhash
    embedding VECTOR(1536),              -- pgvector embedding
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 13.11. Deduplication Strategy

```python
class Deduplicator:
    """
    3-layer deduplication để tránh trùng lặp:
    """

    async def check_duplicate(self, item: ExtractedContent) -> DuplicateCheck:
        # Layer 1: Exact URL match
        existing = await self.db.find_by_url(item.source_url)
        if existing:
            return DuplicateCheck(is_duplicate=True, match=existing, method="url")

        # Layer 2: Fingerprint similarity (MinHash / SimHash)
        fingerprint = self.compute_fingerprint(item.full_text)
        similar_fp = await self.db.find_similar_fingerprint(fingerprint, threshold=0.85)
        if similar_fp:
            return DuplicateCheck(is_duplicate=True, match=similar_fp, method="fingerprint")

        # Layer 3: Semantic similarity (cosine similarity trên embeddings)
        embedding = await self.embed(item.abstract or item.full_text[:2000])
        similar = await self.vector_db.similarity_search(embedding, top_k=3)
        for s in similar:
            if s.similarity > 0.92:
                return DuplicateCheck(is_duplicate=True, match=s, method="semantic")

        return DuplicateCheck(is_duplicate=False)

    def compute_fingerprint(self, text: str) -> str:
        """
        MinHash fingerprint:
        1. Normalize text (lowercase, remove punctuation)
        2. Generate n-grams (shingles, n=5)
        3. Apply MinHash với 128 hash functions
        4. Return hex string
        """
        pass
```

### 13.12. Scheduling & Orchestration

```python
# collector_scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Đăng ký jobs từ config
for source in config.sources:
    scheduler.add_job(
        func=run_collector_pipeline,
        trigger=CronTrigger.from_crontab(source.schedule),
        args=[source.name],
        id=f"collector_{source.name}",
        max_instances=1,          # Không chạy trùng
        coalesce=True,            # Gộp các runs bị missed
    )

async def run_collector_pipeline(source_name: str):
    """Chạy full pipeline cho 1 source"""
    run = await db.create_run(source_name, status="running")

    try:
        # Phase 1: Discover
        collector = get_collector(source_name)
        raw_items = await collector.discover()
        await db.update_run(run, items_discovered=len(raw_items))

        # Phase 2: Extract
        extracted = []
        for raw in raw_items:
            try:
                ext = await collector.extract(raw)
                extracted.append(ext)
                await db.save_raw_item(raw, ext)
            except Exception as e:
                logger.warning(f"Extract failed for {raw.url}: {e}")

        # Phase 3: Evaluate
        evaluator = RelevanceEvaluator()
        for item in extracted:
            eval_result = await evaluator.evaluate(item)
            await db.save_evaluation(item, eval_result)

            # Phase 4: Auto-process high-confidence items
            if eval_result.recommendation == "approve":
                processor = ItemProcessor()
                processed = await processor.process(item, eval_result)
                ingester = GraphIngester()
                await ingester.ingest(processed)
                await db.add_to_review_queue(item, eval_result, status="auto-approved")
            else:
                await db.add_to_review_queue(item, eval_result, status="pending")

        await db.update_run(run, status="success")

    except Exception as e:
        await db.update_run(run, status="error", error_message=str(e))
        await notify_admin(f"Collector {source_name} failed: {e}")
```

### 13.13. API Endpoints

> Xem chi tiết tại Section 7.5 (Collector API endpoints)

### 13.14. Monitoring & Alerting

> Xem UI wireframe tại Section 8.4 (Collector Manager Page)

**Alerting rules cần cấu hình:**
- Source failed 3 lần liên tiếp → notify admin
- High-value item (score ≥ 90) discovered → notify team immediately
- Review queue > 20 items pending → notify reviewers
- Collector hasn't run in 24h → alert
- Duplicate rate > 50% → review source config

### 13.15. Feedback Loop — AI học từ human reviews

```python
class FeedbackLearner:
    """
    Cải thiện evaluation model dựa trên human review decisions.
    Khi human approve/reject items mà AI đánh giá khác → learn.
    """

    async def learn_from_review(self, item, ai_eval, human_decision):
        # Case 1: AI said "reject" but human approved
        # → Under-scored, need to increase weight for certain signals
        if ai_eval.recommendation == "reject" and human_decision == "approve":
            await self.record_correction(item, ai_eval, "under_scored")

        # Case 2: AI said "approve" but human rejected
        # → Over-scored, need to decrease weight for certain signals
        if ai_eval.recommendation == "approve" and human_decision == "reject":
            await self.record_correction(item, ai_eval, "over_scored")

        # Case 3: Human edited tags/relations before approving
        # → AI suggestions were incomplete
        if human_decision == "edited":
            await self.record_tag_correction(item, ai_eval.suggested_tags, human_tags)

    async def update_evaluation_model(self):
        """
        Periodically retrain/tune:
        1. Update relevance scoring prompt với examples từ corrections
        2. Adjust score weights dựa trên human preferences
        3. Update few-shot examples trong prompts
        """
        corrections = await self.db.get_recent_corrections(days=30)
        if len(corrections) > 10:
            updated_prompt = await self.refine_prompt(corrections)
            await self.update_evaluator_prompt(updated_prompt)
```

### 13.16. Advanced: Research Agent — AI tự nghiên cứu

Ngoài thu thập thụ động, hệ thống có thể có **Research Agent** chủ động:

```python
class ResearchAgent:
    """
    AI agent chủ động nghiên cứu sâu về một topic khi được yêu cầu
    hoặc khi phát hiện knowledge gap.
    """

    async def deep_research(self, topic: str, depth: int = 3):
        """
        Multi-step research:
        1. Tìm papers/articles liên quan trên nhiều sources
        2. Đọc và summarize mỗi item
        3. Xác định sub-topics và research tiếp (depth levels)
        4. Tổng hợp thành comprehensive research report
        5. Thêm tất cả items + report vào knowledge graph
        """

        # Level 1: Broad search across all sources
        initial_items = await self.search_all_sources(topic)

        # Level 2: Read, analyze, identify sub-topics
        analysis = await self.analyze_collection(initial_items)
        sub_topics = analysis.key_subtopics  # e.g., ["agent memory types", "memory architectures"]

        # Level 3: Deep dive into each sub-topic
        all_items = initial_items
        for sub in sub_topics:
            if depth > 1:
                sub_items = await self.deep_research(sub, depth - 1)
                all_items.extend(sub_items)

        # Synthesize: create comprehensive research report
        report = await self.synthesize(topic, all_items)

        # Add to knowledge graph
        await self.ingest_research_report(report, all_items)

        return report

    async def auto_fill_gaps(self):
        """
        Tự động phát hiện knowledge gaps và research để lấp đầy.
        Chạy hàng tuần.
        """
        gaps = await self.graph_analyzer.find_gaps()
        # gaps = ["Agent Security", "Agent Cost Optimization", ...]

        for gap in gaps:
            if gap.priority >= 0.7:
                await self.deep_research(gap.topic, depth=2)
```

### 13.17. Chi phí & Tài nguyên ước tính

| Component | Tài nguyên | Chi phí ước tính (self-hosted) |
|---|---|---|
| Collector service | 1 CPU, 1GB RAM | Included in server |
| LLM evaluation (Ollama) | 4-8GB RAM (cho 7B model) | GPU server ~$50-100/mo |
| PDF processing | CPU-intensive, burst | Included in server |
| Browserless (scraping) | 2GB RAM | Included in server |
| Storage (PDFs, cache) | ~10-50GB | $2-5/mo |
| **Total** | **Server 8-core, 32GB RAM** | **~$80-150/mo** |

> **Lưu ý**: Nếu dùng Ollama với model nhỏ (Qwen 2.5 7B, Llama 3.1 8B) thì có thể chạy trên CPU với 16GB RAM, giảm chi phí xuống ~$40-60/mo. Với model lớn hơn (70B) thì cần GPU dedicated server.

### 13.18. Risk & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Source blocks scraping | Mất nguồn dữ liệu | Rotate user-agents, respect robots.txt, dùng API chính thức khi có thể |
| LLM đánh giá sai | Junk data vào graph | Human-in-the-loop cho items score < 75, feedback loop |
| Quá nhiều items cần review | Review fatigue | Tune thresholds, tăng auto-approve threshold dần |
| Duplicate items | Bloated graph | 3-layer deduplication |
| Source API changes | Collector breaks | Monitor collector health, alert on errors, modular collectors |
| LLM cost (nếu dùng API) | Chi phí cao | Dùng local Ollama, cache evaluation results, batch processing |
| Copyright issues | Legal risk | Chỉ store abstract + summary cho papers, link tới full text |
