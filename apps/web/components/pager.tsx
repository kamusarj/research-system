"use client";

/** Điều hướng trang cho các danh sách có phân trang phía máy chủ. */
export function Pager({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <nav className="pager" aria-label="Phân trang">
      <button type="button" className="secondary" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Trang trước
      </button>
      <span>Trang {page}/{pages} · {total} mục</span>
      <button type="button" className="secondary" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Trang sau →
      </button>
    </nav>
  );
}
