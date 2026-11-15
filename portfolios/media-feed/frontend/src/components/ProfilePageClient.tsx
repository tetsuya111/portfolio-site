"use client";

import {
  Box, Container, Avatar, Typography, Button, Tabs, Tab,
  Card, CardMedia, CardContent, Chip, Stack, TextField,
  IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import {
  Edit as EditIcon, PersonAdd as FollowIcon,
  Image as ImageIcon, VideoFile as VideoIcon,
  Download as DownloadIcon,
} from "@mui/icons-material";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Profile, BookmarkedContent, Content, profileApi, followingApi, bookmarkApi, getMediaUrl } from "@/lib/api";
import FeedPlayer from "@/components/FeedPlayer";
import { getUsername, isLoggedIn } from "@/lib/auth";

interface Props {
  username: string;
}

export default function ProfilePageClient({ username }: Props) {
  const router = useRouter();
  const loggedIn = isLoggedIn();
  const currentUser = getUsername();
  const isOwner = currentUser === username;

  const [profile, setProfile] = useState<Profile | null>(null);
  const [localBookmarks, setLocalBookmarks] = useState<BookmarkedContent[]>([]);
  const [tab, setTab] = useState(0);
  const [editOpen, setEditOpen] = useState(false);
  const [description, setDescription] = useState("");
  const [displayDescription, setDisplayDescription] = useState("");
  const [feedContents, setFeedContents] = useState<Content[]>([]);
  const [feedOpen, setFeedOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    Promise.all([
      profileApi.get(username),
      bookmarkApi.list(username),
    ]).then(([profileRes, bookmarksRes]) => {
      setProfile(profileRes.data);
      setDescription(profileRes.data.description ?? "");
      setDisplayDescription(profileRes.data.description ?? "");
      setLocalBookmarks(bookmarksRes.data);
    }).catch(() => {});
  }, [username]);

  const mediaType = tab === 0 ? null : tab === 1 ? "image" : "video";
  const filtered = mediaType
    ? localBookmarks.filter((b) => b.content.type === mediaType)
    : localBookmarks;

  const saveProfile = async () => {
    await profileApi.update(username, { description });
    setDisplayDescription(description);
    setEditOpen(false);
  };

  const removeBookmark = async (id: string) => {
    await bookmarkApi.remove(username, id);
    setLocalBookmarks((prev) => prev.filter((b) => b.id !== id));
  };

  const downloadBookmarks = async () => {
    if (!username || filtered.length === 0) return;
    setDownloading(true);
    try {
      const ids = filtered.map((b) => b.content.id);
      const { data } = await bookmarkApi.download(username, ids);
      const url = URL.createObjectURL(data as Blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "bookmarks.zip";
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  const openBookmarkFeed = (clicked: BookmarkedContent) => {
    const allContents = filtered.map((b) => b.content);
    const idx = allContents.findIndex((c) => c.id === clicked.content.id);
    const reordered = idx > 0
      ? [...allContents.slice(idx), ...allContents.slice(0, idx)]
      : allContents;
    setFeedContents(reordered);
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
    <Box sx={{ pt: 10, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="md" sx={{ py: 3 }}>
        {/* Profile header */}
        <Box sx={{
          bgcolor: "background.paper", borderRadius: 3, p: 3, mb: 3,
          display: "flex", alignItems: "center", gap: 3,
        }}>
          <Avatar
            sx={{ width: 80, height: 80, bgcolor: "primary.main", fontSize: 32 }}
          >
            {username[0]?.toUpperCase()}
          </Avatar>

          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h5" fontWeight={700}>{username}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {displayDescription || "説明なし"}
            </Typography>
          </Box>

          <Box sx={{ display: "flex", gap: 1 }}>
            {isOwner ? (
              <IconButton onClick={() => setEditOpen(true)}>
                <EditIcon />
              </IconButton>
            ) : (
              <>
                <Button
                  variant="contained"
                  startIcon={<FollowIcon />}
                  size="small"
                  onClick={async () => {
                    if (!loggedIn || !currentUser) return;
                    await followingApi.follow(currentUser, username);
                  }}
                >
                  フォロー
                </Button>
              </>
            )}
            <Button
              variant="outlined"
              size="small"
              onClick={() => router.push(`/following/${username}`)}
            >
              フォロー中
            </Button>
          </Box>
        </Box>

        {/* Bookmarks section */}
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>ブックマーク</Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={<DownloadIcon />}
            onClick={downloadBookmarks}
            disabled={downloading || filtered.length === 0}
          >
            {downloading ? "ダウンロード中..." : "一括ダウンロード"}
          </Button>
        </Box>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label="すべて" />
          <Tab icon={<ImageIcon fontSize="small" />} label="画像" iconPosition="start" />
          <Tab icon={<VideoIcon fontSize="small" />} label="動画" iconPosition="start" />
        </Tabs>

        <Grid container spacing={2}>
          {filtered.map((b) => (
            <Grid key={b.id} size={{ xs: 12, sm: 6 }}>
              <Card
                sx={{ cursor: "pointer", bgcolor: "background.paper", position: "relative" }}
                onClick={() => openBookmarkFeed(b)}
              >
                {b.content.type === "video" ? (
                  <CardMedia
                    component="video"
                    src={getMediaUrl(b.content)}
                    sx={{ height: 200, objectFit: "cover" }}
                  />
                ) : (
                  <CardMedia
                    component="img"
                    image={getMediaUrl(b.content)}
                    alt={b.content.title}
                    sx={{ height: 200, objectFit: "cover" }}
                  />
                )}
                <CardContent sx={{ py: 1 }}>
                  <Typography variant="body2" noWrap>{b.content.title || "無題"}</Typography>
                </CardContent>
                {isOwner && (
                  <Button
                    size="small"
                    color="error"
                    sx={{ position: "absolute", top: 4, right: 4, minWidth: 0, p: 0.5 }}
                    onClick={(e) => { e.stopPropagation(); removeBookmark(b.id); }}
                  >
                    ×
                  </Button>
                )}
              </Card>
            </Grid>
          ))}
          {filtered.length === 0 && (
            <Grid size={12}>
              <Typography color="text.secondary" textAlign="center" py={4}>
                ブックマークがありません
              </Typography>
            </Grid>
          )}
        </Grid>
      </Container>

      {/* Edit dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>プロフィール編集</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={3}
            label="説明"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>キャンセル</Button>
          <Button variant="contained" onClick={saveProfile}>保存</Button>
        </DialogActions>
      </Dialog>
    </Box>
    </>
  );
}
