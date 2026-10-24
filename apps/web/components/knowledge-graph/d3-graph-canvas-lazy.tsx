"use client";

import dynamic from "next/dynamic";

// d3 (~250 KB) chỉ cần trên trang đồ thị: tách khỏi bundle chung và không render phía máy chủ.
export const D3GraphCanvas = dynamic(
  () => import("@/components/knowledge-graph/d3-graph-canvas").then((module) => module.D3GraphCanvas),
  {
    ssr: false,
    loading: () => <div className="graph-canvas-skeleton skeleton" role="status" aria-label="Đang tải đồ thị" />,
  },
);
