import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DocumentSourceViewer } from "./document-source-viewer";

vi.mock("@/lib/i18n", () => {
  const t = (key: string) => key;
  return { useI18n: () => ({ t }) };
});

const originalCreateObjectUrl = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
const originalRevokeObjectUrl = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  if (originalCreateObjectUrl) Object.defineProperty(URL, "createObjectURL", originalCreateObjectUrl);
  else Reflect.deleteProperty(URL, "createObjectURL");
  if (originalRevokeObjectUrl) Object.defineProperty(URL, "revokeObjectURL", originalRevokeObjectUrl);
  else Reflect.deleteProperty(URL, "revokeObjectURL");
});

const markdownContent = {
  workspace_id: "workspace-1",
  filename: "agents.md",
  format: "md",
  preview_kind: "markdown" as const,
  source_text: "# Governed agents\n\n- Cite evidence\n\n<script>alert('unsafe')</script>",
  extracted_text: "Governed agents\n\nCite evidence",
  supports_raw: true,
  source_truncated: false,
  editable: true,
  source_version: 1,
};

it("switches between raw, preview and side-by-side modes without executing source HTML", () => {
  const { container } = render(<DocumentSourceViewer content={markdownContent} />);

  expect(screen.getByText("rawSource")).toBeInTheDocument();
  expect(screen.getByText("formattedPreview")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Governed agents" })).toBeInTheDocument();
  expect(container.querySelector(".source-raw-pane > pre > code")).toHaveTextContent("Cite evidence");
  expect(container.querySelector(".document-rendered-preview > .document-preview-paper")).toBeInTheDocument();
  expect(container.querySelector("script")).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "rawView" }));
  expect(screen.getByText("rawSource")).toBeInTheDocument();
  expect(screen.queryByText("formattedPreview")).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "previewView" }));
  expect(screen.queryByText("rawSource")).not.toBeInTheDocument();
  expect(screen.getByText("formattedPreview")).toBeInTheDocument();
});

it("shows extracted DOCX content without offering a binary raw view", () => {
  render(
    <DocumentSourceViewer
      content={{
        ...markdownContent,
        filename: "agents.docx",
        format: "docx",
        preview_kind: "docx",
        source_text: null,
        extracted_text: "Human review remains required.",
        supports_raw: false,
        original_available: true,
      }}
    />,
  );

  expect(screen.queryByRole("button", { name: "rawView" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "sideBySideView" })).not.toBeInTheDocument();
  expect(screen.getByText("Human review remains required.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "downloadOriginal" })).toHaveAttribute(
    "href",
    "/api/v1/documents/workspace-1/original",
  );
});

it("fits an uploaded PDF as a whole page inside its original-file preview", () => {
  render(
    <DocumentSourceViewer
      content={{
        ...markdownContent,
        filename: "research.pdf",
        format: "pdf",
        preview_kind: "pdf",
        source_text: null,
        extracted_text: "Extracted research content.",
        supports_raw: false,
        original_available: true,
        original_preview_kind: "pdf",
      }}
    />,
  );

  expect(screen.getByTitle("originalPdfPreview")).toHaveAttribute(
    "src",
    "/api/v1/documents/workspace-1/original?inline=true#toolbar=1&navpanes=0&view=Fit",
  );
});

it("removes a stale LaTeX PDF while compiling a changed source", async () => {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(
    new Response(new Blob(["%PDF-1.7\n%%EOF"], { type: "application/pdf" }), { status: 200 }),
  ));
  const createObjectUrlMock = vi.fn()
    .mockReturnValueOnce("blob:first-preview")
    .mockReturnValueOnce("blob:second-preview");
  const revokeObjectUrlMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectUrlMock });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectUrlMock });

  const latexContent = {
    ...markdownContent,
    filename: "draft.tex",
    format: "latex",
    preview_kind: "latex" as const,
    source_text: "\\begin{document}\nFirst draft\n\\end{document}",
    extracted_text: "First draft",
  };
  const { rerender, unmount } = render(<DocumentSourceViewer content={latexContent} />);

  const firstFrame = await screen.findByTitle("compiledLatexPreview", {}, { timeout: 2_000 });
  expect(firstFrame).toHaveAttribute(
    "src",
    "blob:first-preview#toolbar=0&navpanes=0&view=Fit",
  );

  rerender(
    <DocumentSourceViewer
      content={{
        ...latexContent,
        source_text: "\\begin{document}\nSecond draft\n\\end{document}",
        extracted_text: "Second draft",
      }}
    />,
  );

  expect(screen.queryByTitle("compiledLatexPreview")).not.toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("latexCompiling");
  await waitFor(() => {
    expect(screen.getByTitle("compiledLatexPreview")).toHaveAttribute(
      "src",
      "blob:second-preview#toolbar=0&navpanes=0&view=Fit",
    );
  }, { timeout: 2_000 });
  expect(revokeObjectUrlMock).toHaveBeenCalledWith("blob:first-preview");

  unmount();
  expect(revokeObjectUrlMock).toHaveBeenCalledWith("blob:second-preview");
});

it("renders only the LaTeX document body instead of its compilation preamble", () => {
  const { container } = render(
    <DocumentSourceViewer
      content={{
        ...markdownContent,
        filename: "robot.tex",
        format: "latex",
        preview_kind: "latex",
        source_text: [
          "% Biên dịch bằng XeLaTeX",
          "\\documentclass{article}",
          "\\usepackage{fontspec}",
          "\\setmainfont{Noto Sans}",
          "\\definecolor{navy}{HTML}{193754}",
          "\\begin{document}",
          "\\section{Robot thông minh}",
          "Nội dung nghiên cứu \\textbf{giữ lại} trong Preview.",
          "\\end{document}",
        ].join("\n"),
        extracted_text: "Robot thông minh\n\nNội dung nghiên cứu giữ lại trong Preview.",
      }}
    />,
  );

  const paper = container.querySelector(".document-preview-paper");
  expect(paper).toHaveTextContent("Robot thông minh");
  expect(paper).toHaveTextContent("Nội dung nghiên cứu giữ lại trong Preview.");
  expect(paper).not.toHaveTextContent("XeLaTeX");
  expect(paper).not.toHaveTextContent("usepackage");
  expect(paper).not.toHaveTextContent("setmainfont");
});

it("removes CV layout macros from the LaTeX body while keeping visible text", () => {
  const { container } = render(
    <DocumentSourceViewer
      content={{
        ...markdownContent,
        filename: "cv.tex",
        format: "latex",
        preview_kind: "latex",
        source_text: [
          "\\begin{document}",
          "\\sidesection{CHỨNG CHỈ}",
          "{\\fontsize{8.8}{11.2}\\selectfont",
          "Google Analytics 4 - 2025\\par",
          "Meta Digital Marketing - 2024\\par",
          "}",
          "\\vspace*{12mm}",
          "\\hspace*{10mm}\\begin{minipage}{127.5mm}",
          "\\RaggedRight",
          "{\\fontsize{24.5}{27}\\selectfont\\bfseries\\color{bodytext}ỨNG VIÊN MẪU}\\par",
          "\\end{minipage}",
          "\\end{document}",
        ].join("\n"),
        extracted_text: "CHỨNG CHỈ\nGoogle Analytics 4 - 2025\nMeta Digital Marketing - 2024\nỨNG VIÊN MẪU",
      }}
    />,
  );

  const paper = container.querySelector(".document-preview-paper");
  expect(paper).toHaveTextContent("CHỨNG CHỈ");
  expect(paper).toHaveTextContent("Google Analytics 4 - 2025");
  expect(paper).toHaveTextContent("ỨNG VIÊN MẪU");
  expect(paper).not.toHaveTextContent("sidesection");
  expect(paper).not.toHaveTextContent("fontsize");
  expect(paper).not.toHaveTextContent("minipage");
  expect(paper).not.toHaveTextContent("RaggedRight");
});

it("renders CV semantic macros as readable sections, jobs and bullet lists", () => {
  const { container } = render(
    <DocumentSourceViewer
      content={{
        ...markdownContent,
        filename: "cv-experience.tex",
        format: "latex",
        preview_kind: "latex",
        source_text: [
          "\\begin{document}",
          "\\mainsection{KINH NGHIỆM LÀM VIỆC}",
          "\\jobheading{DIGITAL MARKETING EXECUTIVE}{06/2024 - HIỆN TẠI}{Công ty ABC Retail}",
          "\\tightbullets",
          "\\item Lập kế hoạch nội dung đa kênh.",
          "\\item Theo dõi báo cáo tuần.",
          "\\closebullets",
          "\\sidesection{KỸ NĂNG}",
          "\\skillbar{Content Marketing}{38.5mm}",
          "\\skillbar{Google Analytics}{33mm}",
          "\\mainsection{HỌC VẤN}",
          "\\end{document}",
        ].join("\n"),
        extracted_text: "Kinh nghiệm làm việc",
      }}
    />,
  );

  const paper = container.querySelector(".document-preview-paper");
  expect(paper).toHaveTextContent("KINH NGHIỆM LÀM VIỆC");
  expect(paper).toHaveTextContent("DIGITAL MARKETING EXECUTIVE");
  expect(paper).toHaveTextContent("06/2024 - HIỆN TẠI · Công ty ABC Retail");
  expect(paper).toHaveTextContent("Lập kế hoạch nội dung đa kênh.");
  expect(paper).toHaveTextContent("HỌC VẤN");
  expect(paper).toHaveTextContent("Content Marketing");
  expect(paper).toHaveTextContent("Google Analytics");
  expect(paper).not.toHaveTextContent("mainsection");
  expect(paper).not.toHaveTextContent("jobheading");
  expect(paper).not.toHaveTextContent("tightbullets");
  expect(paper).not.toHaveTextContent("closebullets");
  expect(paper).not.toHaveTextContent("skillbar");
});
