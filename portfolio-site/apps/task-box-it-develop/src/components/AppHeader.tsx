"use client";

import Link from "next/link";
import { useAuth } from "./AuthProvider";

export function AppHeader() {
  const auth = useAuth();
  return (
    <header className="flex items-center justify-between gap-3 border-b border-stone-200 bg-white/80 px-4 py-3 backdrop-blur">
      <Link href="/" className="text-base font-bold tracking-tight text-stone-800">
        📮 タスク百葉箱
      </Link>
      {auth.status === "authenticated" && (
        <nav className="flex items-center gap-3 text-sm text-stone-600">
          {auth.user.role === "admin" && (
            <>
              <Link href="/chat" className="hover:text-stone-900">チャット</Link>
              <Link href="/admin/summaries" className="hover:text-stone-900">届いた相談</Link>
            </>
          )}
          <span className="hidden max-w-40 truncate sm:inline">{auth.user.display_name}</span>
          <button type="button" onClick={() => auth.logout()} className="rounded-full border border-stone-300 px-3 py-1 hover:bg-stone-100">
            ログアウト
          </button>
        </nav>
      )}
    </header>
  );
}
