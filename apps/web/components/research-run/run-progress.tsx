"use client";

import { STAGE_STEPS, stepStates, type ResearchRun, type ResearchRunEvent } from "@/lib/research-runs";

const STATE_LABEL = { done: "xong", current: "đang chạy", pending: "chưa tới", failed: "lỗi" } as const;

export function RunProgress({ run, events }: { run: ResearchRun; events: ResearchRunEvent[] }) {
  const states = stepStates(run);
  const latest = [...events].reverse().find((event) => event.kind !== "stage") ?? events[events.length - 1];
  return (
    <section className="run-progress" aria-label="Tiến độ nghiên cứu">
      <ol className="run-steps">
        {STAGE_STEPS.map((step, index) => {
          const detail = step.detail(run.metrics);
          return (
            <li key={step.key} className={`run-step ${states[index]}`} aria-current={states[index] === "current" ? "step" : undefined}>
              <span className="run-step-marker" aria-hidden="true" />
              <span className="run-step-label">{step.label}</span>
              <span className="run-step-detail">{detail ?? STATE_LABEL[states[index]]}</span>
              <span className="sr-only">: {STATE_LABEL[states[index]]}</span>
            </li>
          );
        })}
      </ol>
      <p className={`run-latest ${latest?.kind ?? ""}`} role="status" aria-live="polite">
        {latest ? latest.message : "Đang chờ worker nhận việc…"}
      </p>
    </section>
  );
}
