"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Box, Container, Typography, TextField, Select, MenuItem,
  FormControl, InputLabel, Button, Stack, Paper, Snackbar, CircularProgress,
} from "@mui/material";
import { BASE_URL, authApi } from "@/lib/api";
import { isLoggedIn, getUsername, setUserPermissions } from "@/lib/auth";

const COLOR_OPTIONS = [
  { label: "黒", value: "#111111" },
  { label: "濃紺", value: "#1a1a2e" },
  { label: "濃青", value: "#1e3a5f" },
  { label: "紫", value: "#2d1b69" },
  { label: "濃緑", value: "#1a2e1a" },
  { label: "濃赤", value: "#3d1515" },
  { label: "白", value: "#ffffff" },
];

const DEFAULT = {
  cols: "3",
  rows: "3",
  tile_size: "150",
  color: "#1a1a2e",
  keyword: "",
};

export default function BlogPartsCreateClient() {
  const router = useRouter();
  const [form, setForm] = useState(DEFAULT);
  const [previewHtml, setPreviewHtml] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [embedHtml, setEmbedHtml] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    authApi.me().then(({ data }) => {
      setUserPermissions(data);
      if (!data.is_affiliate) router.replace("/feed");
    }).catch(() => router.replace("/feed"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const username = getUsername() ?? "";
  const apiBase = typeof window !== "undefined"
    ? `${window.location.origin}${BASE_URL}`
    : BASE_URL;
  const siteUrl = typeof window !== "undefined" ? window.location.origin : "";

  const buildSrc = (f: typeof form) => {
    const params = new URLSearchParams({
      cols: f.cols,
      rows: f.rows,
      tile_size: f.tile_size,
      color: f.color,
      site_url: siteUrl,
      affiliate_user_id: username,
    });
    if (f.keyword) params.set("keyword", f.keyword);
    return `${apiBase}/blog-parts/?${params.toString()}`;
  };

  const handleCreate = async () => {
    const src = buildSrc(form);
    const cols = Number(form.cols);
    const rows = Number(form.rows);
    const size = Number(form.tile_size);
    const w = cols * (size + 8) + 16;
    const h = rows * (size + 8) + 16;
    setEmbedHtml(`<iframe src="${src}" width="${w}" height="${h}" frameborder="0" scrolling="no"></iframe>`);

    setPreviewLoading(true);
    try {
      const res = await fetch(src);
      const html = await res.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const bodyHtml = doc.body.innerHTML;
      const styleContent = Array.from(doc.head.querySelectorAll("style"))
        .map((s) => s.textContent ?? "")
        .join("");
      const scopedStyle = styleContent.replace(/\bbody\b/g, "#blog-parts-preview");
      setPreviewHtml(`<style>${scopedStyle}</style>${bodyHtml}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleReset = () => {
    setForm(DEFAULT);
    setPreviewHtml("");
    setEmbedHtml("");
  };

  return (
    <Box sx={{ pt: 10, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="md" sx={{ py: 3 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>
          ブログパーツ作成
        </Typography>

        <Paper sx={{ p: 3, bgcolor: "background.paper", borderRadius: 2, mb: 3 }}>
          <Stack spacing={2.5}>
            <Stack direction="row" spacing={2}>
              <TextField
                label="列数"
                type="number"
                value={form.cols}
                onChange={(e) => setForm((p) => ({ ...p, cols: e.target.value }))}
                inputProps={{ min: 1, max: 10 }}
                size="small"
                sx={{ width: 120 }}
              />
              <TextField
                label="行数"
                type="number"
                value={form.rows}
                onChange={(e) => setForm((p) => ({ ...p, rows: e.target.value }))}
                inputProps={{ min: 1, max: 10 }}
                size="small"
                sx={{ width: 120 }}
              />
              <TextField
                label="一辺の長さ (px)"
                type="number"
                value={form.tile_size}
                onChange={(e) => setForm((p) => ({ ...p, tile_size: e.target.value }))}
                inputProps={{ min: 80, max: 400 }}
                size="small"
                sx={{ width: 160 }}
              />
            </Stack>

            <Stack direction="row" spacing={2} alignItems="center">
              <FormControl size="small" sx={{ width: 180 }}>
                <InputLabel>色</InputLabel>
                <Select
                  value={form.color}
                  label="色"
                  onChange={(e) => setForm((p) => ({ ...p, color: e.target.value }))}
                >
                  {COLOR_OPTIONS.map((c) => (
                    <MenuItem key={c.value} value={c.value}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box sx={{ width: 16, height: 16, bgcolor: c.value, border: "1px solid #555", borderRadius: 0.5 }} />
                        {c.label}
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                label="キーワード"
                value={form.keyword}
                onChange={(e) => setForm((p) => ({ ...p, keyword: e.target.value }))}
                size="small"
                sx={{ flexGrow: 1 }}
                placeholder="記事タイトル・説明で絞り込み"
              />
            </Stack>

            <Stack direction="row" spacing={2}>
              <Button variant="contained" onClick={handleCreate}>作成</Button>
              <Button variant="outlined" onClick={handleReset}>リセット</Button>
            </Stack>
          </Stack>
        </Paper>

        {(previewHtml || previewLoading || embedHtml) && (
          <>
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
              プレビュー
            </Typography>
            <Box sx={{ overflowX: "auto", mb: 3, minHeight: 40 }}>
              {previewLoading ? (
                <CircularProgress size={28} />
              ) : (
                <Box
                  id="blog-parts-preview"
                  dangerouslySetInnerHTML={{ __html: previewHtml }}
                />
              )}
            </Box>

            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
              埋め込みコード
            </Typography>
            <Paper
              sx={{
                p: 2, bgcolor: "#1a1a1a", borderRadius: 1,
                fontFamily: "monospace", fontSize: 13, color: "#ccc",
                wordBreak: "break-all", position: "relative",
              }}
            >
              {embedHtml}
              <Button
                size="small"
                variant="outlined"
                sx={{ position: "absolute", top: 8, right: 8 }}
                onClick={() => {
                  navigator.clipboard.writeText(embedHtml);
                  setCopied(true);
                }}
              >
                コピー
              </Button>
            </Paper>
          </>
        )}
      </Container>

      <Snackbar
        open={copied}
        autoHideDuration={2000}
        onClose={() => setCopied(false)}
        message="コピーしました"
      />
    </Box>
  );
}
