"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Box, Container, Typography, TextField, Button, CircularProgress,
  Card, CardMedia, CardContent, Checkbox, Chip, Stack, Pagination,
  InputAdornment, IconButton, Alert, Collapse,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import { Search as SearchIcon, Close as CloseIcon, ExpandMore as ExpandMoreIcon, ExpandLess as ExpandLessIcon } from "@mui/icons-material";
import { useRouter } from "next/navigation";
import { Content, Tag, contentsApi, tagsApi, articlesApi, getMediaUrl, authApi } from "@/lib/api";
import { getUsername, isLoggedIn, setUserPermissions } from "@/lib/auth";

const COLS = 3;
const ROWS = 5;
const PAGE_SIZE = COLS * ROWS;

export default function ArticleCreateClient() {
  const router = useRouter();

  useEffect(() => {
    if (!isLoggedIn()) { router.replace("/login"); return; }
    authApi.me().then(({ data }) => {
      setUserPermissions(data);
      if (!data.is_author) router.replace("/feed");
    }).catch(() => router.replace("/feed"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [selectedFilterTags, setSelectedFilterTags] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  const [contents, setContents] = useState<Content[]>([]);
  const [totalContents, setTotalContents] = useState(0);
  const [page, setPage] = useState(1);
  const [loadingContents, setLoadingContents] = useState(false);

  const [tagFilterOpen, setTagFilterOpen] = useState(false);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [selectedContents, setSelectedContents] = useState<Content[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    tagsApi.list().then(({ data }) => setAllTags(data));
  }, []);

  const fetchContents = useCallback(async (pg: number) => {
    setLoadingContents(true);
    try {
      const params: Record<string, string | string[]> = { page: String(pg) };
      if (searchQuery) params.q = searchQuery;
      if (selectedFilterTags.length) params.tag = selectedFilterTags;
      const { data } = await contentsApi.list(params);
      setContents(data.results);
      setTotalContents(data.count);
    } finally {
      setLoadingContents(false);
    }
  }, [searchQuery, selectedFilterTags]);

  useEffect(() => {
    setPage(1);
    fetchContents(1);
  }, [selectedFilterTags]);

  const handleSearch = () => {
    setPage(1);
    fetchContents(1);
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, pg: number) => {
    setPage(pg);
    fetchContents(pg);
  };

  const toggleCheck = (content: Content) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(content.id)) {
        next.delete(content.id);
      } else {
        next.add(content.id);
      }
      return next;
    });
  };

  const handleAdd = () => {
    const toAdd = contents.filter((c) => checkedIds.has(c.id) && !selectedContents.find((s) => s.id === c.id));
    setSelectedContents((prev) => [...prev, ...toAdd]);
    setCheckedIds(new Set());
  };

  const handleRemoveSelected = (id: string) => {
    setSelectedContents((prev) => prev.filter((c) => c.id !== id));
  };

  const handleCreate = async () => {
    if (!title.trim()) {
      setError("タイトルを入力してください");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await articlesApi.create({
        title,
        description,
        content_ids: selectedContents.map((c) => c.id),
      });
      setSuccess(true);
      setTimeout(() => router.push("/feed"), 1500);
    } catch {
      setError("記事の作成に失敗しました");
    } finally {
      setSubmitting(false);
    }
  };

  const totalPages = Math.ceil(totalContents / PAGE_SIZE);

  return (
    <Box sx={{ pt: 8, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 3, fontWeight: 700 }}>
          記事作成
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 2 }}>記事を作成しました</Alert>}

        {/* タイトル・説明 */}
        <Stack spacing={2} sx={{ mb: 4 }}>
          <TextField
            label="タイトル"
            fullWidth
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
          <TextField
            label="説明"
            fullWidth
            multiline
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </Stack>

        {/* 選択済みコンテンツ一覧 */}
        {selectedContents.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
              選択済みコンテンツ ({selectedContents.length}件)
            </Typography>
            <Grid container spacing={1}>
              {selectedContents.map((content) => (
                <Grid key={content.id} size={{ xs: 4, sm: 3, md: 2 }}>
                  <Box sx={{ position: "relative" }}>
                    <Card sx={{ bgcolor: "background.paper" }}>
                      {content.type === "video" ? (
                        <CardMedia
                          component="video"
                          src={getMediaUrl(content)}
                          sx={{ height: 80, objectFit: "cover" }}
                        />
                      ) : (
                        <CardMedia
                          component="img"
                          image={getMediaUrl(content)}
                          alt={content.title}
                          sx={{ height: 80, objectFit: "cover" }}
                        />
                      )}
                      <CardContent sx={{ py: 0.5, px: 1 }}>
                        <Typography variant="caption" noWrap>{content.title || "無題"}</Typography>
                      </CardContent>
                    </Card>
                    <IconButton
                      size="small"
                      onClick={() => handleRemoveSelected(content.id)}
                      sx={{
                        position: "absolute", top: 2, left: 2,
                        bgcolor: "rgba(0,0,0,0.6)", color: "#fff",
                        width: 20, height: 20,
                        "&:hover": { bgcolor: "error.main" },
                      }}
                    >
                      <CloseIcon sx={{ fontSize: 14 }} />
                    </IconButton>
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}

        {/* コンテンツ選択欄 */}
        <Box sx={{ mb: 2 }}>
          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
            コンテンツ選択
          </Typography>

          {/* 検索 */}
          <TextField
            fullWidth
            placeholder="タイトル・説明で検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            size="small"
            sx={{ mb: 1 }}
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton onClick={handleSearch} size="small">
                    <SearchIcon fontSize="small" />
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />

          {/* タグフィルター（開閉可能） */}
          <Box sx={{ mb: 2 }}>
            <Button
              size="small"
              variant="outlined"
              endIcon={tagFilterOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              onClick={() => setTagFilterOpen((v) => !v)}
              sx={{ mb: 1 }}
            >
              タグで絞り込む {selectedFilterTags.length > 0 && `(${selectedFilterTags.length})`}
            </Button>
            <Collapse in={tagFilterOpen}>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, pt: 0.5 }}>
                {allTags.map((tag) => (
                  <Chip
                    key={tag.name}
                    label={`#${tag.name}`}
                    size="small"
                    clickable
                    onClick={() =>
                      setSelectedFilterTags((prev) =>
                        prev.includes(tag.name) ? prev.filter((t) => t !== tag.name) : [...prev, tag.name]
                      )
                    }
                    color={selectedFilterTags.includes(tag.name) ? "primary" : "default"}
                    variant={selectedFilterTags.includes(tag.name) ? "filled" : "outlined"}
                  />
                ))}
              </Box>
            </Collapse>
          </Box>

          {/* コンテンツタイル */}
          {loadingContents ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Grid container spacing={1}>
              {contents.map((content) => (
                <Grid key={content.id} size={{ xs: 12 / COLS }}>
                  <Box sx={{ position: "relative" }}>
                    <Card
                      sx={{
                        bgcolor: "background.paper",
                        outline: checkedIds.has(content.id) ? "2px solid" : "none",
                        outlineColor: "primary.main",
                        cursor: "pointer",
                      }}
                      onClick={() => toggleCheck(content)}
                    >
                      {content.type === "video" ? (
                        <CardMedia
                          component="video"
                          src={getMediaUrl(content)}
                          sx={{ height: 120, objectFit: "cover" }}
                        />
                      ) : (
                        <CardMedia
                          component="img"
                          image={getMediaUrl(content)}
                          alt={content.title}
                          sx={{ height: 120, objectFit: "cover" }}
                        />
                      )}
                      <CardContent sx={{ py: 0.5, px: 1 }}>
                        <Typography variant="caption" noWrap>{content.title || "無題"}</Typography>
                      </CardContent>
                    </Card>
                    <Checkbox
                      checked={checkedIds.has(content.id)}
                      onChange={() => toggleCheck(content)}
                      onClick={(e) => e.stopPropagation()}
                      size="small"
                      sx={{
                        position: "absolute", top: 2, left: 2,
                        color: "#fff", p: 0.25,
                        bgcolor: "rgba(0,0,0,0.4)",
                        borderRadius: 1,
                        "&.Mui-checked": { color: "primary.main" },
                      }}
                    />
                  </Box>
                </Grid>
              ))}
            </Grid>
          )}

          {/* ページネーション + 追加ボタン */}
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mt: 2 }}>
            {totalPages > 1 && (
              <Pagination
                count={totalPages}
                page={page}
                onChange={handlePageChange}
                size="small"
                color="primary"
              />
            )}
            <Button
              variant="outlined"
              onClick={handleAdd}
              disabled={checkedIds.size === 0}
              sx={{ ml: "auto" }}
            >
              追加 ({checkedIds.size})
            </Button>
          </Box>
        </Box>

        {/* 作成ボタン */}
        <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 3 }}>
          <Button
            variant="contained"
            size="large"
            onClick={handleCreate}
            disabled={submitting || !title.trim()}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
          >
            作成
          </Button>
        </Box>
      </Container>
    </Box>
  );
}
