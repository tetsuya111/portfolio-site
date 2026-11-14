"use client";

import { useState, useCallback, useEffect } from "react";
import {
  Box, Container, TextField, InputAdornment, IconButton,
  Card, CardMedia, CardContent, Typography, Chip,
  Stack, Accordion, AccordionSummary, AccordionDetails,
  ToggleButton, ToggleButtonGroup,
  Button, CircularProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import {
  Search as SearchIcon,
  ExpandMore,
  Shuffle as ShuffleIcon,
  Image as ImageIcon,
  VideoFile as VideoIcon,
} from "@mui/icons-material";
import { useSearchParams } from "next/navigation";
import { ExpandLess } from "@mui/icons-material";
import { Content, Tag, contentsApi, tagsApi, getMediaUrl } from "@/lib/api";
import FeedPlayer from "@/components/FeedPlayer";

export default function SearchPageClient() {
  const urlParams = useSearchParams();
  const initialQuery = urlParams.get("q") ?? "";
  const initialType = urlParams.get("type") ?? "";
  const initialTagParam = urlParams.get("tag");
  const initialTags = initialTagParam ? [initialTagParam] : [];

  const [contents, setContents] = useState<Content[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState(initialQuery);
  const [selectedTags, setSelectedTags] = useState<string[]>(initialTags);
  const [contentType, setContentType] = useState(initialType);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [feedContents, setFeedContents] = useState<Content[]>([]);
  const [feedOpen, setFeedOpen] = useState(false);
  const [tagCloudOpen, setTagCloudOpen] = useState(false);

  const buildParams = useCallback(() => {
    const p: Record<string, string | string[]> = {};
    if (query) p.q = query;
    if (selectedTags.length) p.tag = selectedTags;
    if (contentType) p.type = contentType;
    return p;
  }, [query, selectedTags, contentType]);

  useEffect(() => {
    const p: Record<string, string | string[]> = {};
    if (initialQuery) p.q = initialQuery;
    if (initialTags.length) p.tag = initialTags;
    if (initialType) p.type = initialType;

    Promise.all([
      contentsApi.list(p),
      tagsApi.list(),
    ]).then(([contentsRes, tagsRes]) => {
      setContents(contentsRes.data.results);
      setTotal(contentsRes.data.count);
      setAllTags(tagsRes.data);
    }).catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const search = async (reset = true) => {
    setLoading(true);
    try {
      const p = buildParams();
      const pg = reset ? 1 : page + 1;
      const { data } = await contentsApi.list({ ...p, page: String(pg) });
      if (reset) {
        setContents(data.results);
        setPage(1);
      } else {
        setContents((prev) => [...prev, ...data.results]);
        setPage(pg);
      }
      setTotal(data.count);
    } finally {
      setLoading(false);
    }
  };

  const toggleTag = (name: string) => {
    setSelectedTags((prev) =>
      prev.includes(name) ? prev.filter((t) => t !== name) : [...prev, name]
    );
  };

  const openFeed = async (content: Content) => {
    try {
      const { data } = await contentsApi.related(content.id);
      setFeedContents([content, ...data.results.filter((c) => c.id !== content.id)]);
    } catch {
      setFeedContents([content]);
    }
    setFeedOpen(true);
  };

  return (
    <>
    {feedOpen && (
      <Box sx={{ position: "fixed", inset: 0, zIndex: 2000 }}>
        <FeedPlayer
          initialContents={feedContents}
          totalCount={feedContents.length}
          onClose={() => setFeedOpen(false)}
        />
      </Box>
    )}
    <Box sx={{ pt: 8, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        {/* Search bar */}
        <TextField
          fullWidth
          placeholder="タイトル・説明で検索..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search()}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton onClick={() => search()}><SearchIcon /></IconButton>
              </InputAdornment>
            ),
          }}
          variant="outlined"
          sx={{ mb: 2 }}
        />

        {/* Advanced search */}
        <Accordion sx={{ mb: 2, bgcolor: "background.paper" }}>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="body2">詳細検索</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Stack spacing={2}>
              <ToggleButtonGroup
                value={contentType}
                exclusive
                onChange={(_, v) => setContentType(v ?? "")}
                size="small"
              >
                <ToggleButton value=""><Typography variant="caption">すべて</Typography></ToggleButton>
                <ToggleButton value="image"><ImageIcon fontSize="small" /><Typography variant="caption" sx={{ ml: 0.5 }}>画像</Typography></ToggleButton>
                <ToggleButton value="video"><VideoIcon fontSize="small" /><Typography variant="caption" sx={{ ml: 0.5 }}>動画</Typography></ToggleButton>
              </ToggleButtonGroup>

              <Box sx={{ display: "flex", gap: 1 }}>
                <Button
                  variant="contained"
                  startIcon={<SearchIcon />}
                  onClick={() => search()}
                  disabled={loading}
                >
                  検索
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<ShuffleIcon />}
                  onClick={async () => {
                    const { data } = await contentsApi.list({ ...buildParams(), random: "true" });
                    setContents(data.results);
                    setTotal(data.count);
                  }}
                >
                  ランダム
                </Button>
              </Box>
            </Stack>
          </AccordionDetails>
        </Accordion>

        {/* Tag cloud */}
        <Box sx={{ mb: 3 }}>
          <Box
            sx={{ display: "flex", alignItems: "center", cursor: "pointer", mb: tagCloudOpen ? 1 : 0 }}
            onClick={() => setTagCloudOpen((v) => !v)}
          >
            <Typography variant="subtitle2" sx={{ color: "text.secondary", flexGrow: 1 }}>
              タグ {selectedTags.length > 0 && `(${selectedTags.length}件選択中)`}
            </Typography>
            {tagCloudOpen ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
          </Box>
          {tagCloudOpen && (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {allTags.map((tag) => (
                <Chip
                  key={tag.name}
                  label={`#${tag.name} (${tag.content_count})`}
                  size="small"
                  clickable
                  onClick={() => toggleTag(tag.name)}
                  color={selectedTags.includes(tag.name) ? "primary" : "default"}
                  variant={selectedTags.includes(tag.name) ? "filled" : "outlined"}
                />
              ))}
            </Box>
          )}
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {total} 件
        </Typography>

        {/* Results grid */}
        <Grid container spacing={2}>
          {contents.map((content) => (
            <Grid key={content.id} size={{ xs: 12, sm: 6 }}>
              <Card
                sx={{
                  cursor: "pointer",
                  "&:hover": { transform: "scale(1.02)", transition: "transform 0.2s" },
                  bgcolor: "background.paper",
                }}
                onClick={() => openFeed(content)}
              >
                {content.type === "video" ? (
                  <CardMedia
                    component="video"
                    src={getMediaUrl(content)}
                    sx={{ height: 240, objectFit: "cover" }}
                  />
                ) : (
                  <CardMedia
                    component="img"
                    image={getMediaUrl(content)}
                    alt={content.title}
                    sx={{ height: 240, objectFit: "cover" }}
                  />
                )}
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" noWrap>{content.title || "無題"}</Typography>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
                    {content.tags.slice(0, 3).map((t) => (
                      <Chip key={t.name} label={t.name} size="small" sx={{ height: 18, fontSize: 10 }} />
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Load more */}
        {contents.length < total && (
          <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
            <Button
              variant="outlined"
              onClick={() => search(false)}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={16} /> : undefined}
            >
              もっと見る
            </Button>
          </Box>
        )}
      </Container>
    </Box>
    </>
  );
}
