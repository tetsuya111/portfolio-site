"use client";

import { useEffect, useRef, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, Box, Typography, CircularProgress,
} from "@mui/material";
import { api } from "@/lib/api";
import { setTurnstileVerified } from "@/lib/auth";

declare global {
  interface Window {
    turnstile?: {
      render: (el: HTMLElement, options: Record<string, unknown>) => string;
      execute: (widgetId: string) => void;
      reset: (widgetId: string) => void;
    };
    onTurnstileLoad?: () => void;
  }
}

interface Props {
  onVerified: () => void;
}

export default function TurnstileDialog({ onVerified }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const sitekey = process.env.NEXT_PUBLIC_CLOUDFLARE_TURNSTILE_SITE_KEY ?? "";

    const renderWidget = () => {
      if (!containerRef.current || widgetIdRef.current || !window.turnstile) return;
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey,
        execution: "render",
        callback: async (token: string) => {
          setLoading(true);
          setError("");
          try {
            const { data } = await api.post("/auth/turnstile/", { token });
            if (data.success) {
              setTurnstileVerified();
              onVerified();
            } else {
              setError("認証に失敗しました。もう一度お試しください。");
              if (widgetIdRef.current) window.turnstile?.reset(widgetIdRef.current);
            }
          } catch {
            setError("認証エラーが発生しました。");
            if (widgetIdRef.current) window.turnstile?.reset(widgetIdRef.current);
          } finally {
            setLoading(false);
          }
        },
        "expired-callback": () => {
          if (widgetIdRef.current) window.turnstile?.reset(widgetIdRef.current);
        },
      });
    };

    if (window.turnstile) {
      renderWidget();
    } else {
      window.onTurnstileLoad = renderWidget;
    }

    return () => {
      widgetIdRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Dialog
      open
      disableEscapeKeyDown
      sx={{ zIndex: 3000 }}
      PaperProps={{
        sx: { bgcolor: "#111", borderRadius: 3, textAlign: "center", minWidth: 320, p: 1 },
      }}
    >
      <DialogTitle sx={{ color: "primary.main", fontWeight: 700 }}>
        ※アクセス認証※
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          認証しないとコンテンツはみれません！
        </Typography>
        <Box sx={{ display: "flex", justifyContent: "center", mb: 1 }}>
          <div ref={containerRef} />
        </Box>
        {loading && <CircularProgress size={20} sx={{ mt: 1 }} />}
        {error && (
          <Typography variant="caption" color="error" sx={{ mt: 1, display: "block" }}>
            {error}
          </Typography>
        )}
      </DialogContent>
    </Dialog>
  );
}
