"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Box, Typography, Chip, CircularProgress } from "@mui/material";
import FeedPlayer from "@/components/FeedPlayer";
import { Article, Content, articlesApi, contentsApi } from "@/lib/api";

interface Props {
  id: string;
}

export default function ArticlePageClient({ id }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [article, setArticle] = useState<Article | null>(null);
  const [contents, setContents] = useState<Content[]>([]);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const affiliateUserId = searchParams.get("affiliate_user_id");
    const t = searchParams.get("t");
    const params: Record<string, string> = {};
    if (affiliateUserId) params.affiliate_user_id = affiliateUserId;
    if (t) params.t = t;

    articlesApi.get(Number(id), Object.keys(params).length ? params : undefined).then(async (res) => {
      const art = res.data;
      setArticle(art);
      const articleContents: Content[] = art.contents ?? [];

      let relatedContents: Content[] = [];
      if (articleContents.length > 0) {
        const lastContent = articleContents[articleContents.length - 1];
        try {
          const { data } = await contentsApi.related(lastContent.id);
          const articleIds = new Set(articleContents.map((c) => c.id));
          relatedContents = data.results.filter((c) => !articleIds.has(c.id));
        } catch {}
      }

      setContents([...articleContents, ...relatedContents]);
    }).catch(() => setNotFound(true));
  }, [id]);

  if (notFound) {
    return (
      <Box sx={{ pt: 10, display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Typography color="text.secondary">記事が見つかりません</Typography>
      </Box>
    );
  }

  if (!article) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (contents.length === 0) {
    return (
      <Box sx={{ pt: 10, display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Typography color="text.secondary">コンテンツがありません</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ position: "relative", width: "100vw", height: "100vh" }}>
      {/* 記事タイトルオーバーレイ */}
      <Box
        sx={{
          position: "fixed",
          top: 40,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 1300,
          bgcolor: "rgba(0,0,0,0.55)",
          backdropFilter: "blur(6px)",
          borderRadius: 2,
          px: 2,
          py: 0.5,
          maxWidth: "70vw",
          textAlign: "center",
          pointerEvents: "none",
        }}
      >
        <Typography
          variant="caption"
          sx={{ color: "rgba(255,255,255,0.9)", fontWeight: 600, fontSize: 12, lineHeight: 1.4 }}
          noWrap
        >
          {article.title}
        </Typography>
        {article.article_tags.length > 0 && (
          <Box sx={{ display: "flex", gap: 0.5, justifyContent: "center", flexWrap: "wrap", mt: 0.25 }}>
            {article.article_tags.slice(0, 3).map((t) => (
              <Chip
                key={t.name}
                label={`#${t.name}`}
                size="small"
                sx={{ height: 16, fontSize: 9, bgcolor: "rgba(255,68,88,0.4)", color: "#fff" }}
              />
            ))}
          </Box>
        )}
      </Box>

      <FeedPlayer
        initialContents={contents}
        totalCount={contents.length}
        queryParams={{}}
        onClose={() => router.back()}
      />
    </Box>
  );
}
