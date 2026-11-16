"use client";

// ログイン後の画面の共通枠（ヘッダー・ナビゲーション・認証チェック）。

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { RequireAuth, useAuth } from "@/lib/auth";
import { ROLE_LABEL } from "@/lib/format";

interface NavItem {
  href: string;
  label: string;
  adminOnly?: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "ダッシュボード" },
  { href: "/products/", label: "商品" },
  { href: "/inventory/", label: "在庫" },
  { href: "/inventory/record/", label: "入出庫" },
  { href: "/inventory/history/", label: "履歴" },
  { href: "/users/", label: "ユーザー", adminOnly: true },
];

function isActive(pathname: string, href: string): boolean {
  const normalize = (p: string) => (p.endsWith("/") ? p : `${p}/`);
  return normalize(pathname) === normalize(href);
}

export function AppShell({
  title,
  children,
  adminOnly = false,
}: {
  title: string;
  children: ReactNode;
  adminOnly?: boolean;
}) {
  const { user, signOut } = useAuth();
  const pathname = usePathname() ?? "/";

  return (
    <div className="shell">
      <header className="header">
        <Link href="/" className="brand">
          在庫管理
        </Link>
        <nav className="nav" aria-label="メインメニュー">
          {NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "admin").map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={isActive(pathname, item.href) ? "nav-link active" : "nav-link"}
              aria-current={isActive(pathname, item.href) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        {user && (
          <div className="account">
            <span>
              {user.username}（{ROLE_LABEL[user.role]}）
            </span>
            <button type="button" className="button secondary small" onClick={signOut}>
              ログアウト
            </button>
          </div>
        )}
      </header>
      <main className="main">
        <h1>{title}</h1>
        <RequireAuth adminOnly={adminOnly}>{children}</RequireAuth>
      </main>
    </div>
  );
}
