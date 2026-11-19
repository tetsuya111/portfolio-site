import type { Metadata, Viewport } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { AgeGate } from "@/components/AgeGate";

import "./globals.css";

export const metadata: Metadata = {
  title: "AVイベント情報DB",
  description: "複数サイトのAV女優イベント情報をまとめて検索・地図表示できる情報サイト",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <header className="header">
          <Link href="/" className="brand">
            AVイベント情報DB
          </Link>
          <nav className="nav" aria-label="メインメニュー">
            <Link href="/" className="nav-link">
              検索
            </Link>
            <Link href="/map/" className="nav-link">
              地図
            </Link>
          </nav>
        </header>
        <main className="main">
          <AgeGate>{children}</AgeGate>
        </main>
        <footer className="footer muted">
          掲載情報は各サイトの告知を自動で収集したものです。最新の情報は取得元のページでご確認ください。
        </footer>
      </body>
    </html>
  );
}
