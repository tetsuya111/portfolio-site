"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as apiClient from "@/lib/api";
import type { User } from "@/lib/types";

export const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "anonymous"; user: null }
  | { status: "authenticated"; user: User };

type AuthContextValue = AuthState & {
  login: (credential: string) => Promise<void>;
  devLogin: (admin: boolean) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });

  useEffect(() => {
    let active = true;
    apiClient.restoreSession().then((user) => {
      if (active) setState(user ? { status: "authenticated", user } : { status: "anonymous", user: null });
    });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (credential: string) => {
    const user = await apiClient.loginWithGoogle(credential);
    setState({ status: "authenticated", user });
  }, []);

  const devLogin = useCallback(async (admin: boolean) => {
    const user = await apiClient.loginForDevelopment(admin);
    setState({ status: "authenticated", user });
  }, []);

  const logout = useCallback(async () => {
    await apiClient.logout();
    setState({ status: "anonymous", user: null });
  }, []);

  const value = useMemo(() => ({ ...state, login, devLogin, logout }), [state, login, devLogin, logout]);

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    </GoogleOAuthProvider>
  );
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth は AuthProvider の中で使ってください");
  return value;
}

/**
 * ログインが必要な画面を包む。表示の制御であり、認可はバックエンドが行う。
 * 未ログインは /login へ、管理者でないユーザーが管理者画面を開いた場合は /chat へ送る。
 */
export function RequireAuth({ admin = false, children }: { admin?: boolean; children: React.ReactNode }) {
  const auth = useAuth();
  const router = useRouter();
  const denied = auth.status === "authenticated" && admin && auth.user.role !== "admin";

  useEffect(() => {
    if (auth.status === "anonymous") router.replace("/login");
    else if (denied) router.replace("/chat");
  }, [auth.status, denied, router]);

  if (auth.status !== "authenticated" || denied) {
    return <p className="p-8 text-center text-sm text-stone-500">読み込んでいます…</p>;
  }
  return <>{children}</>;
}
