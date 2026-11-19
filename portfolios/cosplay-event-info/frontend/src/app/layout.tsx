import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { SiteHeader } from "@/components/SiteHeader";

import "./globals.css";

export const metadata: Metadata = {
  title: "コスプレイベント情報まとめ",
  description:
    "複数サイトのコスプレイベントの予定とコスプレイヤーの情報をまとめて検索できるサイト（Next.js + Django REST Framework）",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <SiteHeader />
        <main className="container">{children}</main>
        <footer className="site-footer container">
          情報は各取得元サイトから自動で収集しています。最新の情報は取得元・公式サイトでご確認ください。
        </footer>
      </body>
    </html>
  );
}
