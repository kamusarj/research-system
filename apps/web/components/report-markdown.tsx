import type { ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { isSafeLink } from "@/components/chat-markdown";

type CiteHandler = (citation: number) => void;

function plainText(children: ReactNode): string {
  if (typeof children === "string" || typeof children === "number") return String(children);
  if (Array.isArray(children)) return children.map(plainText).join("");
  return "";
}

/**
 * Báo cáo nghiên cứu dạng Markdown. Liên kết có nhãn là số (`[3](url)`) là trích dẫn: hiển thị
 * thành nút nguồn nhỏ; khi có `onCite` thì bấm sẽ mở bảng bằng chứng thay vì rời trang (vẫn giữ
 * href để mở tab mới hoặc dùng bàn phím). HTML thô bị bỏ qua, chỉ cho phép liên kết an toàn.
 */
export function ReportMarkdown({ content, onCite, activeCitation }: { content: string; onCite?: CiteHandler; activeCitation?: number | null }) {
  const components: Components = {
    a: ({ href, children }) => {
      if (!isSafeLink(href)) return <span>{children}</span>;
      const label = plainText(children).trim();
      const external = !href.startsWith("/");
      if (/^\d{1,3}$/.test(label)) {
        const citation = Number(label);
        return (
          <a
            className={`citation${activeCitation === citation ? " active" : ""}`}
            href={href}
            target={external ? "_blank" : undefined}
            rel="noreferrer"
            aria-label={`Nguồn ${citation}`}
            onClick={(event) => {
              if (!onCite || event.metaKey || event.ctrlKey || event.shiftKey) return;
              event.preventDefault();
              onCite(citation);
            }}
          >
            {citation}
          </a>
        );
      }
      return <a href={href} target={external ? "_blank" : undefined} rel="noreferrer">{children}</a>;
    },
    img: () => null,
  };
  return (
    <div className="report-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components} skipHtml>
        {content}
      </ReactMarkdown>
    </div>
  );
}
