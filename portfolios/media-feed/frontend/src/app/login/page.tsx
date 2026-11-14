"use client";

import { useState } from "react";
import { Box, Container, Typography, TextField, Button, Tab, Tabs, Alert } from "@mui/material";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [tab, setTab] = useState(0);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!username || !password) { setError("ユーザー名とパスワードを入力してください"); return; }
    setLoading(true);
    setError("");
    try {
      if (tab === 0) {
        const { data } = await authApi.login(username, password);
        localStorage.setItem("access_token", data.access);
        localStorage.setItem("refresh_token", data.refresh);
        localStorage.setItem("username", username);
        router.push("/feed");
        router.refresh();
      } else {
        await authApi.register(username, password);
        const { data } = await authApi.login(username, password);
        localStorage.setItem("access_token", data.access);
        localStorage.setItem("refresh_token", data.refresh);
        localStorage.setItem("username", username);
        router.push("/feed");
        router.refresh();
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || (tab === 0 ? "ログインに失敗しました" : "登録に失敗しました"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ pt: 10, minHeight: "100vh", display: "flex", alignItems: "center", bgcolor: "background.default" }}>
      <Container maxWidth="xs">
        <Box sx={{ bgcolor: "background.paper", borderRadius: 3, p: 4 }}>
          <Typography variant="h5" fontWeight={700} textAlign="center" sx={{ mb: 2, color: "primary.main" }}>
            StreamVault
          </Typography>

          <Tabs value={tab} onChange={(_, v) => setTab(v)} centered sx={{ mb: 3 }}>
            <Tab label="ログイン" />
            <Tab label="新規登録" />
          </Tabs>

          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <TextField
            fullWidth
            label="ユーザー名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="パスワード"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            sx={{ mb: 3 }}
          />

          <Button
            fullWidth
            variant="contained"
            size="large"
            onClick={handleSubmit}
            disabled={loading}
            sx={{ borderRadius: 20 }}
          >
            {tab === 0 ? "ログイン" : "登録"}
          </Button>
        </Box>
      </Container>
    </Box>
  );
}
