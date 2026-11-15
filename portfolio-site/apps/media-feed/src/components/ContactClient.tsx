"use client";

import { useState } from "react";
import {
  Box, Container, Typography, TextField, Button,
  Paper, Alert, CircularProgress,
} from "@mui/material";
import { inquiryApi } from "@/lib/api";

const EMPTY = { name: "", title: "", email: "", content: "" };

export default function ContactClient() {
  const [form, setForm] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((p) => ({ ...p, [key]: e.target.value }));

  const handleSubmit = async () => {
    const { name, title, email, content } = form;
    if (!name || !title || !email || !content) {
      setError("全ての項目を入力してください");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await inquiryApi.send(form);
      setSuccess(true);
      setForm(EMPTY);
    } catch {
      setError("送信に失敗しました。しばらくしてから再度お試しください。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ pt: 10, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="sm" sx={{ py: 4 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>
          お問い合わせ
        </Typography>

        {success ? (
          <Alert severity="success" sx={{ borderRadius: 2 }}>
            お問い合わせを受け付けました。ご連絡ありがとうございます。
          </Alert>
        ) : (
          <Paper sx={{ p: 3, bgcolor: "background.paper", borderRadius: 2 }}>
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <TextField
                label="名前"
                required
                value={form.name}
                onChange={set("name")}
                size="small"
                fullWidth
              />
              <TextField
                label="タイトル"
                required
                value={form.title}
                onChange={set("title")}
                size="small"
                fullWidth
              />
              <TextField
                label="メールアドレス"
                required
                type="email"
                value={form.email}
                onChange={set("email")}
                size="small"
                fullWidth
              />
              <TextField
                label="内容"
                required
                multiline
                rows={6}
                value={form.content}
                onChange={set("content")}
                fullWidth
              />

              {error && <Alert severity="error" sx={{ borderRadius: 1 }}>{error}</Alert>}

              <Button
                variant="contained"
                onClick={handleSubmit}
                disabled={loading}
                startIcon={loading ? <CircularProgress size={16} /> : undefined}
                sx={{ alignSelf: "flex-start" }}
              >
                {loading ? "送信中..." : "送信"}
              </Button>
            </Box>
          </Paper>
        )}
      </Container>
    </Box>
  );
}
