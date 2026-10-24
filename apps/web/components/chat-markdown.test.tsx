import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import { ChatMarkdown, ChatMedia } from "./chat-markdown";

it("renders GFM structure instead of exposing raw Markdown or HTML", () => {
  const { container } = render(
    <ChatMarkdown content={[
      "## Implementation",
      "",
      "Use **human review**:",
      "",
      "- validate",
      "- approve",
      "",
      "```ts",
      "const safe = true;",
      "```",
      "",
      "<script>alert('unsafe')</script>",
    ].join("\n")} />,
  );

  expect(screen.getByRole("heading", { name: "Implementation" })).toBeInTheDocument();
  expect(screen.getByText("human review").tagName).toBe("STRONG");
  expect(screen.getByRole("list")).toBeInTheDocument();
  expect(screen.getByText("const safe = true;")).toBeInTheDocument();
  expect(container.querySelector("script")).toBeNull();
  expect(screen.queryByText("**human review**")).not.toBeInTheDocument();
});

it("renders only allowlisted public ChatGPT image assets without a referrer", () => {
  const { container } = render(
    <ChatMedia media={[
      {
        type: "image",
        url: "https://files.oaiusercontent.com/public/diagram.png?sig=test",
        alt: "Governed agent diagram",
      },
      {
        type: "image",
        url: "/api/v1/chat/messages/message-123/media/0",
        alt: "Locally cached ChatGPT image",
      },
      {
        type: "image",
        url: "https://evil.example/tracker.png",
        alt: "Blocked tracker",
      },
    ]} />,
  );

  const image = screen.getByRole("img", { name: "Governed agent diagram" });
  expect(image).toHaveAttribute("loading", "lazy");
  expect(image).toHaveAttribute("referrerpolicy", "no-referrer");
  expect(screen.getByRole("img", { name: "Locally cached ChatGPT image" })).toBeInTheDocument();
  expect(container.querySelectorAll("img")).toHaveLength(2);
  expect(screen.queryByRole("img", { name: "Blocked tracker" })).not.toBeInTheDocument();
});
