"use client";

import {
  Box, Container, Typography, Chip, TextField, InputAdornment,
  ToggleButtonGroup, ToggleButton, Stack,
} from "@mui/material";
import { Search as SearchIcon, Sort as SortIcon } from "@mui/icons-material";
import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Tag, tagsApi } from "@/lib/api";

type SortMode = "count" | "name";

export default function TagsPageClient() {
  const router = useRouter();
  const [tags, setTags] = useState<Tag[]>([]);
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<SortMode>("count");

  useEffect(() => {
    tagsApi.list().then(({ data }) => setTags(data)).catch(() => {});
  }, []);

  const displayed = useMemo(() => {
    let list = filter
      ? tags.filter((t) => t.name.toLowerCase().includes(filter.toLowerCase()))
      : tags;
    if (sort === "count") {
      list = [...list].sort((a, b) => (b.content_count ?? 0) - (a.content_count ?? 0));
    } else {
      list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    }
    return list;
  }, [tags, filter, sort]);

  const maxCount = useMemo(
    () => Math.max(...tags.map((t) => t.content_count ?? 0), 1),
    [tags]
  );

  const getFontSize = (count: number) => {
    const ratio = count / maxCount;
    return 11 + ratio * 20;
  };

  return (
    <Box sx={{ pt: { xs: 8, sm: 10 }, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 2, color: "primary.main" }}>
          タグ一覧
          <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            ({tags.length}件)
          </Typography>
        </Typography>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 3 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="タグ名で絞り込み..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />
          <ToggleButtonGroup
            value={sort}
            exclusive
            onChange={(_, v) => v && setSort(v)}
            size="small"
            sx={{ flexShrink: 0 }}
          >
            <ToggleButton value="count" sx={{ px: 2, gap: 0.5 }}>
              <SortIcon fontSize="small" />
              <Typography variant="caption">件数順</Typography>
            </ToggleButton>
            <ToggleButton value="name" sx={{ px: 2 }}>
              <Typography variant="caption">名前順</Typography>
            </ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
            p: { xs: 2, sm: 3 },
            bgcolor: "background.paper",
            borderRadius: 3,
            minHeight: 200,
          }}
        >
          {displayed.map((tag) => (
            <Chip
              key={tag.name}
              label={
                <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  <span style={{ fontSize: getFontSize(tag.content_count ?? 0) }}>
                    #{tag.name}
                  </span>
                  <Typography
                    component="span"
                    variant="caption"
                    sx={{ color: "text.secondary", fontSize: 10, flexShrink: 0 }}
                  >
                    {tag.content_count}
                  </Typography>
                </Box>
              }
              clickable
              onClick={() => router.push(`/feed?tag=${encodeURIComponent(tag.name)}`)}
              variant="outlined"
              sx={{
                height: "auto",
                py: 0.5,
                borderRadius: 2,
                "&:hover": { bgcolor: "primary.main", color: "white", borderColor: "primary.main" },
                transition: "all 0.15s",
              }}
            />
          ))}
          {displayed.length === 0 && (
            <Typography color="text.secondary">タグが見つかりません</Typography>
          )}
        </Box>
      </Container>
    </Box>
  );
}
