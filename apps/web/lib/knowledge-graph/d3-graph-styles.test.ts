import { describe, expect, it } from "vitest";
import {
  canvasPalette,
  cardEdgePath,
  edgeBezierPath,
  nodeCardMetrics,
  resolveCanvasTheme,
} from "./d3-graph-styles";

describe("nodeCardMetrics", () => {
  it("keeps cards compact but wide enough for the label and degree emphasis", () => {
    const small = nodeCardMetrics("Tìm kiếm", 0);
    const large = nodeCardMetrics("Một nhãn rất dài cần được cắt bớt", 30);

    expect(small.height).toBe(44);
    expect(small.radius).toBe(10);
    expect(small.accentWidth).toBe(4);
    expect(small.width).toBeGreaterThanOrEqual(104);
    expect(large.width).toBeLessThanOrEqual(210);
    expect(nodeCardMetrics("Agent memory", 20).width).toBeGreaterThan(nodeCardMetrics("Agent memory", 0).width);
  });
});

describe("edgeBezierPath", () => {
  it("draws one smooth cubic curve with horizontal tangents", () => {
    const path = edgeBezierPath(0, 0, 200, 50);

    expect(path).toBe("M 0 0 C 64 0, 136 50, 200 50");
    expect(edgeBezierPath(0, 0, 200, 50)).toBe(path);
    expect(edgeBezierPath(10, 10, 10, 10)).toContain("C");
  });
});

describe("cardEdgePath", () => {
  it("leaves the right border of the source card and enters the left border of the target", () => {
    const path = cardEdgePath(0, 0, 100, 300, 0, 80);

    expect(path.startsWith("M 50 0")).toBe(true);
    expect(path.endsWith("260 0")).toBe(true);
  });
});

describe("canvasPalette", () => {
  it("separates the Weave dark canvas from the paper light one", () => {
    const light = canvasPalette("light");
    const dark = canvasPalette("dark");

    expect(light.cardFill).toBe("#ffffff");
    expect(dark.cardFill).toBe("#202027");
    expect(dark.cardStroke).toContain("255,255,255");
    expect(light.hierarchyCardFill).toBe("#ffffff");
    expect(dark.hierarchyCardFill).toBe("#202027");
  });
});

describe("resolveCanvasTheme", () => {
  it("follows the explicit data-theme first", () => {
    expect(resolveCanvasTheme({ getAttribute: () => "dark" })).toBe("dark");
    expect(resolveCanvasTheme({ getAttribute: () => "light" })).toBe("light");
    expect(resolveCanvasTheme({ getAttribute: () => null })).toBe("light");
  });
});
