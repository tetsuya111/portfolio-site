import type { Metadata } from "next";
import Script from "next/script";
import { AppRouterCacheProvider } from "@mui/material-nextjs/v15-appRouter";
import ThemeRegistry from "@/components/ThemeRegistry";
import Navbar from "@/components/Navbar";
import TurnstileGuard from "@/components/TurnstileGuard";

export const metadata: Metadata = {
  title: "StreamVault",
  description: "コンテンツ収集・閲覧サービス",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body style={{ margin: 0, background: "#0a0a0a" }}>
        <Script
          src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad&render=explicit"
          strategy="afterInteractive"
        />
        <AppRouterCacheProvider>
          <ThemeRegistry>
            <Navbar />
            <TurnstileGuard />
            {children}
          </ThemeRegistry>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
