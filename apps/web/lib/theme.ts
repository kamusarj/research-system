export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "research-theme";

// Chạy trong <head> trước khi trang được vẽ để không nháy sáng→tối. Chuỗi tĩnh, không chứa dữ
// liệu người dùng; lỗi truy cập storage (chế độ riêng tư) được bỏ qua.
export const THEME_BOOT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark"){document.documentElement.dataset.theme=t;}}catch(e){}})();`;

export function readThemePreference(): ThemePreference {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

export function applyThemePreference(preference: ThemePreference) {
  const root = document.documentElement;
  if (preference === "system") delete root.dataset.theme;
  else root.dataset.theme = preference;
  try {
    if (preference === "system") window.localStorage.removeItem(THEME_STORAGE_KEY);
    else window.localStorage.setItem(THEME_STORAGE_KEY, preference);
  } catch {
    // Không lưu được lựa chọn (storage bị chặn): giao diện vẫn đổi trong phiên hiện tại.
  }
}

export function nextThemePreference(current: ThemePreference): ThemePreference {
  return current === "system" ? "light" : current === "light" ? "dark" : "system";
}
