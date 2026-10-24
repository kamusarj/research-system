# Exec Plan

Status: đã làm xong phase 1–3; phase 4 chờ chủ máy tạo `GEMINI_API_KEY`.

## Goal

Thêm Gemini Embedding 2 (API miễn phí) làm nhà cung cấp embedding, giữ Mistral.

## Scope

`search_projection.py` (client chung, Gemini, factory, embed_query, lọc model), các nơi gọi
(`api/search.py`, `document_rag.py`, `graph_chat.py`, `scripts/verify_search_projections.py`),
`config.py`, test, `.env.example`, README, decision. Không migration.

## Risk Classification

High-risk: external systems (nhà cung cấp mới), audit/security (nội dung tài liệu tới gói miễn
phí), existing behavior (truy vấn RAG/tìm kiếm).

## Work Phases

1. Tách vòng thử lại/kiểm tra vector thành lớp chung; thêm Gemini client và factory.
2. Thêm `embed_query`, lọc vector theo provider/model; cập nhật nơi gọi.
3. Unit test Gemini (định dạng request, tiền tố, lô, thứ tự, 429 retryDelay, lỗi), test lọc model;
   toàn bộ API pytest, Ruff.
4. Có `GEMINI_API_KEY`: gọi thật, chuyển `.env`, khởi động lại, lập chỉ mục lại RAG tài liệu.

## Stop Conditions

Nếu gemini-embedding-2 không cho 1024 chiều hoặc gói miễn phí không dùng được với khóa của chủ
máy, dừng và hỏi trước khi đổi số chiều/migration.
