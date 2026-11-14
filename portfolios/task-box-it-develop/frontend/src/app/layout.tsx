import type { Metadata, Viewport } from "next";
import { AppHeader } from "@/components/AppHeader";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "タスク百葉箱",
  description: "「こんなツールがほしい」を、おしゃべりするだけで気軽に相談できます。",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja" className="h-full antialiased">
      <body className="flex h-full flex-col">
        <AuthProvider>
          <AppHeader />
          <main className="flex min-h-0 flex-1 flex-col">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
