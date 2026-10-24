"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FormEvent, createContext, useContext, useEffect, useState } from "react";
import { AUTH_EXPIRED_EVENT, ApiError, api, setCsrfCookieName } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export type Role = "owner" | "researcher" | "viewer";

export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role: Role;
  active: boolean;
  password_configured: boolean;
  created_at?: string | null;
  updated_at?: string | null;
};

type AuthConfig = { enabled: boolean; mode: string; csrf_cookie_name: string };
type AuthState = { enabled: boolean; user: AuthUser };
type RequiredRole = Role;

const roleLevel: Record<Role, number> = { viewer: 1, researcher: 2, owner: 3 };
const localOwner: AuthUser = {
  id: "local-user",
  name: "Chủ sở hữu cục bộ",
  email: "local@research.system",
  role: "owner",
  active: true,
  password_configured: false,
};

type AuthContextValue = {
  enabled: boolean;
  loading: boolean;
  user: AuthUser | null;
  error: string | null;
  sessionExpired: boolean;
  can: (role: RequiredRole) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  enabled: false,
  loading: false,
  user: localOwner,
  error: null,
  sessionExpired: false,
  can: () => true,
  login: async () => {},
  logout: async () => {},
  reload: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      // Hai yêu cầu chạy song song: chờ tuần tự làm cả ứng dụng chậm thêm một vòng mạng.
      const [config, me] = await Promise.all([
        api<AuthConfig>("/auth/config"),
        api<AuthState>("/auth/me").then(
          (state) => ({ state, error: null as unknown }),
          (error: unknown) => ({ state: null, error }),
        ),
      ]);
      setEnabled(config.enabled);
      setCsrfCookieName(config.csrf_cookie_name);
      if (me.state) {
        setUser(me.state.user);
      } else if (config.enabled && me.error instanceof ApiError && me.error.status === 401) {
        setUser(null);
      } else {
        throw me.error;
      }
    } catch (requestError) {
      setUser(null);
      setError(requestError instanceof Error ? requestError.message : "Dịch vụ xác thực chưa sẵn sàng");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void reload(); }, []);

  // Phiên hết hạn giữa chừng (sau AUTH_SESSION_HOURS) phải đưa về màn đăng nhập thay vì để mọi
  // truy vấn lỗi 401 trong khi thanh trên cùng vẫn hiện người dùng cũ.
  useEffect(() => {
    if (!enabled) return;
    function expire() {
      setUser((current) => {
        if (current) setSessionExpired(true);
        return null;
      });
      queryClient.clear();
    }
    window.addEventListener(AUTH_EXPIRED_EVENT, expire);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, expire);
  }, [enabled, queryClient]);

  async function login(email: string, password: string) {
    setError(null);
    try {
      await api<AuthState>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        throw new Error("Email hoặc mật khẩu không đúng.");
      }
      throw requestError;
    }
    // Xác nhận trình duyệt đã lưu cookie phiên: cookie Secure bị bỏ qua khi mở qua HTTP thường.
    let state: AuthState;
    try {
      state = await api<AuthState>("/auth/me");
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        throw new Error("Trình duyệt chưa lưu phiên đăng nhập. Hãy mở hệ thống bằng địa chỉ https:// do quản trị viên cung cấp.");
      }
      throw requestError;
    }
    queryClient.clear();
    setSessionExpired(false);
    setUser(state.user);
  }

  async function logout() {
    try {
      await api<void>("/auth/logout", { method: "POST" });
    } catch {
      // Phiên có thể đã hết hạn phía máy chủ; vẫn rời phiên ở trình duyệt.
    } finally {
      queryClient.clear();
      setUser(null);
    }
  }

  const value: AuthContextValue = {
    enabled,
    loading,
    user,
    error,
    sessionExpired,
    can: (requiredRole) => Boolean(user && roleLevel[user.role] >= roleLevel[requiredRole]),
    login,
    logout,
    reload,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { enabled, loading, user, error, sessionExpired, login, reload } = useAuth();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setLoginError(null);
    try {
      await login(email, password);
      setPassword("");
    } catch (requestError) {
      setLoginError(requestError instanceof Error ? requestError.message : t("signInFailed"));
    } finally {
      setSubmitting(false);
    }
  }

  // Vẽ khung ứng dụng ngay trong lúc kiểm tra phiên (kể cả HTML từ máy chủ) thay vì một vòng
  // xoay toàn màn hình; API vẫn tự kiểm tra quyền nên không lộ dữ liệu khi chưa đăng nhập.
  if (loading) return <>{children}</>;
  if (error) return (
    <div className="auth-screen">
      <section className="auth-card">
        <span className="brand-logo" aria-hidden="true">✦</span>
        <h1>{t("authUnavailable")}</h1>
        <p>{error}</p>
        <button onClick={() => void reload()}>{t("retry")}</button>
      </section>
    </div>
  );
  if (enabled && !user) return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <span className="brand-logo" aria-hidden="true">✦</span>
        <p className="eyebrow">Hệ thống nghiên cứu</p>
        <h1>{t("signIn")}</h1>
        <p>{t("signInIntro")}</p>
        {sessionExpired && <p className="notice" role="status">Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại để tiếp tục.</p>}
        <label>{t("email")}<input type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
        <label>{t("password")}<input type="password" autoComplete="current-password" minLength={12} value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
        {loginError && <p className="notice error-notice" role="alert">{loginError}</p>}
        <button disabled={submitting}>{submitting ? t("signingIn") : t("signIn")}</button>
      </form>
    </div>
  );
  return children;
}

export function useAuth() { return useContext(AuthContext); }
