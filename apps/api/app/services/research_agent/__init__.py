"""Nghiên cứu sâu: câu hỏi → báo cáo có trích dẫn đã kiểm chứng.

Luồng: planner (truy vấn theo 5 góc nhìn) → searcher (SearXNG + kho nội bộ, tải trang an toàn,
cache, khử trùng) → verifier (khớp trích dẫn nguyên văn + kiểm tra suy luận) → writer (chỉ dùng
nhận định đã kiểm chứng; máy chủ gắn link nguồn cho từng câu).
"""
