"use client";

import { useState, useEffect } from "react";
import {
  Box, Container, Typography, Card, CardMedia, CardContent,
  Chip, Stack, CircularProgress, TextField, InputAdornment,
  IconButton, Pagination,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import { Search as SearchIcon } from "@mui/icons-material";
import { useRouter } from "next/navigation";
import { Article, articlesApi, getMediaUrl } from "@/lib/api";

const PAGE_SIZE = 20;

function ArticleCard({ article, onClick }: { article: Article; onClick: () => void }) {
  const thumb = article.thumbnail;
  const thumbUrl = thumb ? getMediaUrl(thumb) : "";

  return (
    <Card
      onClick={onClick}
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.paper",
        cursor: "pointer",
        "&:hover": { transform: "scale(1.02)", transition: "transform 0.15s" },
      }}
    >
      <Box sx={{ flex: 3, minHeight: 0, overflow: "hidden", bgcolor: "#111" }}>
        {thumbUrl ? (
          <CardMedia
            component="img"
            image={thumbUrl}
            alt={article.title}
            sx={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        ) : (
          <Box sx={{ width: "100%", height: "100%", minHeight: 150, bgcolor: "#222", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Typography variant="caption" color="text.secondary">No Image</Typography>
          </Box>
        )}
      </Box>
      <CardContent sx={{ flex: 1, py: 1, px: 1.5 }}>
        <Typography variant="body2" fontWeight={600} noWrap>{article.title}</Typography>
        {article.article_tags.length > 0 && (
          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            {article.article_tags.slice(0, 3).map((t) => (
              <Chip key={t.name} label={`#${t.name}`} size="small" sx={{ height: 18, fontSize: 10 }} />
            ))}
          </Stack>
        )}
      </CardContent>
    </Card>
  );
}

export default function ArticlesPageClient() {
  const router = useRouter();
  const [articles, setArticles] = useState<Article[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [inputQuery, setInputQuery] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = { page: String(page), page_size: String(PAGE_SIZE) };
    if (query) params.q = query;
    articlesApi.list(params)
      .then(({ data }) => {
        setArticles(data.results);
        setTotalCount(data.count);
      })
      .finally(() => setLoading(false));
  }, [query, page]);

  const handleSearch = () => {
    setPage(1);
    setQuery(inputQuery);
  };

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  return (
    <Box sx={{ pt: 8, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>記事一覧</Typography>

        <TextField
          fullWidth
          size="small"
          placeholder="タイトル・説明で検索..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          sx={{ mb: 3 }}
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

        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress />
          </Box>
        ) : articles.length === 0 ? (
          <Typography color="text.secondary" sx={{ textAlign: "center", py: 8 }}>
            記事が見つかりません
          </Typography>
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {totalCount} 件
            </Typography>
            <Grid container spacing={2}>
              {articles.map((article) => (
                <Grid key={article.id} size={{ xs: 6, sm: 4, md: 3 }}>
                  <Box sx={{ height: 220, display: "flex", flexDirection: "column" }}>
                    <ArticleCard article={article} onClick={() => router.push(`/articles/${article.id}`)} />
                  </Box>
                </Grid>
              ))}
            </Grid>
            {totalPages > 1 && (
              <Box sx={{ display: "flex", justifyContent: "center", mt: 4 }}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={(_, v) => setPage(v)}
                  color="primary"
                />
              </Box>
            )}
          </>
        )}
      </Container>
    </Box>
  );
}
