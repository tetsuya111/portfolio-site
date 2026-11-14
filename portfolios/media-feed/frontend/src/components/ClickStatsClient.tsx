"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Box, Container, Typography, Select, MenuItem, FormControl,
  InputLabel, Paper, Table, TableHead, TableRow, TableCell,
  TableBody, Chip, CircularProgress,
} from "@mui/material";
import { clickCountApi, ClickCountItem, authApi } from "@/lib/api";
import { isLoggedIn, setUserPermissions } from "@/lib/auth";

const PERIOD_OPTIONS = [
  { label: "全期間", value: "" },
  { label: "今日", value: "today" },
  { label: "7日間", value: "7days" },
  { label: "30日間", value: "30days" },
];

export default function ClickStatsClient() {
  const router = useRouter();
  const [period, setPeriod] = useState("");
  const [count, setCount] = useState(0);
  const [results, setResults] = useState<ClickCountItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    authApi.me().then(({ data }) => {
      setUserPermissions(data);
      if (!data.is_affiliate) router.replace("/feed");
    }).catch(() => router.replace("/feed"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setLoading(true);
    clickCountApi.get(period || undefined)
      .then(({ data }) => {
        setCount(data.count);
        setResults(data.results);
      })
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <Box sx={{ pt: 10, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>
          クリック集計
        </Typography>

        <Paper sx={{ p: 3, bgcolor: "background.paper", borderRadius: 2, mb: 3 }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 3, flexWrap: "wrap" }}>
            <FormControl size="small" sx={{ width: 160 }}>
              <InputLabel>期間</InputLabel>
              <Select
                value={period}
                label="期間"
                onChange={(e) => setPeriod(e.target.value)}
              >
                {PERIOD_OPTIONS.map((p) => (
                  <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box>
              <Typography variant="caption" color="text.secondary">有効クリック数</Typography>
              <Typography variant="h4" fontWeight={700} color="primary.main">
                {loading ? <CircularProgress size={32} /> : count.toLocaleString()}
              </Typography>
            </Box>
          </Box>
        </Paper>

        {!loading && results.length > 0 && (
          <Paper sx={{ bgcolor: "background.paper", borderRadius: 2, overflow: "hidden" }}>
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: "rgba(255,255,255,0.04)" }}>
                    <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>日時</TableCell>
                    <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>ページ</TableCell>
                    <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>参照元</TableCell>
                    <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>IP</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {results.map((item) => (
                    <TableRow key={item.id} sx={{ "&:hover": { bgcolor: "rgba(255,255,255,0.02)" } }}>
                      <TableCell sx={{ whiteSpace: "nowrap", fontSize: 12 }}>
                        {new Date(item.created_at).toLocaleString("ja-JP")}
                      </TableCell>
                      <TableCell sx={{ fontSize: 12, maxWidth: 300 }}>
                        <Typography
                          variant="caption"
                          sx={{
                            display: "block", overflow: "hidden",
                            textOverflow: "ellipsis", whiteSpace: "nowrap",
                          }}
                          title={item.page_link}
                        >
                          {item.page_link}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ fontSize: 12, maxWidth: 250 }}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{
                            display: "block", overflow: "hidden",
                            textOverflow: "ellipsis", whiteSpace: "nowrap",
                          }}
                          title={item.referrer}
                        >
                          {item.referrer || "—"}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={item.ip_address ?? "—"}
                          size="small"
                          sx={{ fontSize: 10, height: 18 }}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Paper>
        )}

        {!loading && results.length === 0 && (
          <Typography color="text.secondary" textAlign="center" py={6}>
            データがありません
          </Typography>
        )}
      </Container>
    </Box>
  );
}
