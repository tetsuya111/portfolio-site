"use client";

// ログイン状態（ユーザー情報・トークン）を画面全体で共有する。

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  apiFetch,
  clearToken,
  getToken,
  login,
  setToken,
  setUnauthorizedHandler,
} from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  /** 起動時にユーザー情報を取得できなかった理由（401 以外。サーバー停止など） */
  error: string | null;
  signIn: (username: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const signOut = useCallback(() => {
    clearToken();
    setUser(null);
    router.replace("/login");
  }, [router]);

  useEffect(() => {
    setUnauthorizedHandler(signOut);
    return () => setUnauthorizedHandler(null);
  }, [signOut]);

  useEffect(() => {
    let cancelled = false;
    const load = getToken()
      ? apiFetch<User>("/users/me")
          .then((me) => {
            if (!cancelled) setUser(me);
          })
          .catch((e) => {
            // トークンが無効（401）のときだけ捨てる。通信エラー・5xx ではトークンを残す。
            if (e instanceof ApiError && e.status === 401) {
              clearToken();
            } else if (!cancelled) {
              setError(e instanceof ApiError ? e.message : "ユーザー情報を取得できませんでした。");
            }
          })
      : Promise.resolve();
    load.finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const token = await login(username, password);
    setToken(token.access_token);
    try {
      setUser(await apiFetch<User>("/users/me"));
      setError(null);
    } catch (error) {
      clearToken();
      throw error;
    }
  }, []);

  const value = useMemo(
    () => ({ user, loading, error, signIn, signOut }),
    [user, loading, error, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth は AuthProvider の内側で使ってください。");
  return ctx;
}

/** ログインしていなければログイン画面へ移す。adminOnly なら管理者以外にはメッセージを出す。 */
export function RequireAuth({ children, adminOnly = false }: { children: ReactNode; adminOnly?: boolean }) {
  const { user, loading, error } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user && !error) router.replace("/login");
  }, [loading, user, error, router]);

  if (!loading && !user && error) {
    return (
      <div className="alert" role="alert">
        <p>{error}</p>
        <button type="button" className="button secondary small" onClick={() => window.location.reload()}>
          再読み込み
        </button>
      </div>
    );
  }
  if (loading || !user) return <p className="muted">読み込み中…</p>;
  if (adminOnly && user.role !== "admin") {
    return <p className="alert">この画面は管理者のみ利用できます。</p>;
  }
  return <>{children}</>;
}
