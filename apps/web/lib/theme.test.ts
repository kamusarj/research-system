import { afterEach, describe, expect, it } from "vitest";
import { applyThemePreference, nextThemePreference, readThemePreference, THEME_STORAGE_KEY } from "./theme";

describe("theme preference", () => {
  afterEach(() => {
    window.localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("cycles system → light → dark → system", () => {
    expect(nextThemePreference("system")).toBe("light");
    expect(nextThemePreference("light")).toBe("dark");
    expect(nextThemePreference("dark")).toBe("system");
  });

  it("stores explicit choices and clears them for system", () => {
    applyThemePreference("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(readThemePreference()).toBe("dark");
    applyThemePreference("system");
    expect(document.documentElement.dataset.theme).toBeUndefined();
    expect(readThemePreference()).toBe("system");
  });

  it("ignores unknown stored values", () => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "neon");
    expect(readThemePreference()).toBe("system");
  });
});
