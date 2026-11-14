import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Billboard → Spotify Playlist",
  description: "Billboard Hot 100 のチャートから Spotify プレイリストを作成します",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // Dark Reader などのブラウザ拡張が <html> に属性を足すことによる hydration 警告を抑える。
    // この要素自身の属性だけが対象で、子要素の不一致は引き続き警告される。
    <html lang="ja" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
