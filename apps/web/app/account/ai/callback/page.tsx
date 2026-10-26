"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { completeChatGPTPlan, readCallbackParams } from "@/lib/chatgpt-plan";

/** ChatGPT chuyển về đây sau khi người dùng đồng ý; hoàn tất trong đúng phiên đăng nhập này. */
export default function ChatGPTPlanCallbackPage() {
  const router = useRouter();
  const started = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // StrictMode chạy effect hai lần; mã ủy quyền chỉ dùng được một lần.
    if (started.current) return;
    started.current = true;
    const params = readCallbackParams(window.location.search);
    // Bỏ mã khỏi thanh địa chỉ và lịch sử trình duyệt ngay lập tức.
    window.history.replaceState(null, "", window.location.pathname);
    if (!params) {
      setError("Liên kết kết nối không hợp lệ. Hãy bắt đầu lại từ trang Tài khoản.");
      return;
    }
    completeChatGPTPlan(params)
      .then((status) => router.replace(status.status === "active" ? "/account?chatgpt=connected" : "/account"))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Không hoàn tất được kết nối ChatGPT."));
  }, [router]);

  return (
    <section className="panel account-panel">
      <div className="section-heading compact"><div><p className="eyebrow">Tài khoản</p><h1>Kết nối gói ChatGPT</h1></div></div>
      {error ? (
        <>
          <p className="notice error-notice" role="alert">{error}</p>
          <Link href="/account" className="secondary-link">Về trang Tài khoản</Link>
        </>
      ) : (
        <p className="muted" role="status">Đang hoàn tất kết nối…</p>
      )}
    </section>
  );
}
