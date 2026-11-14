"use client";

import { useState, useEffect } from "react";
import {
  Box, Container, Typography, TextField, InputAdornment,
  IconButton, List, ListItem, ListItemText, Button, Chip,
} from "@mui/material";
import { Search as SearchIcon, PersonAdd as FollowIcon, Check as CheckIcon } from "@mui/icons-material";
import { useRouter } from "next/navigation";
import { UserProfile, usersApi, followingApi } from "@/lib/api";
import { isLoggedIn, getUsername } from "@/lib/auth";

export default function UsersPageClient() {
  const router = useRouter();
  const loggedIn = isLoggedIn();
  const currentUser = getUsername();

  const [users, setUsers] = useState<UserProfile[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [followedSet, setFollowedSet] = useState<Set<string>>(new Set());

  useEffect(() => {
    usersApi.list().then(({ data }) => setUsers(data)).catch(() => {});
  }, []);

  const search = async (q: string) => {
    setLoading(true);
    try {
      const { data } = await usersApi.list(q || undefined);
      setUsers(data);
    } finally {
      setLoading(false);
    }
  };

  const handleFollow = async (username: string) => {
    if (!loggedIn || !currentUser) return;
    await followingApi.follow(currentUser, username);
    setFollowedSet((prev) => new Set([...prev, username]));
  };

  return (
    <Box sx={{ pt: 8, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="sm" sx={{ py: 3 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>ユーザー一覧</Typography>

        <TextField
          fullWidth
          placeholder="説明で検索..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && search(query)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start"><SearchIcon /></InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <IconButton onClick={() => search(query)} disabled={loading}>
                  <SearchIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
          variant="outlined"
          sx={{ mb: 2 }}
        />

        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          {users.length} 件
        </Typography>

        <List disablePadding>
          {users.map((u) => (
            <ListItem
              key={u.username}
              sx={{
                bgcolor: "background.paper", mb: 1, borderRadius: 2,
                px: 2, py: 1.5, cursor: "pointer",
                "&:hover": { bgcolor: "action.hover" },
              }}
              secondaryAction={
                u.username !== currentUser && loggedIn ? (
                  followedSet.has(u.username) ? (
                    <Chip
                      icon={<CheckIcon />}
                      label="フォロー中"
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  ) : (
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={<FollowIcon />}
                      onClick={(e) => { e.stopPropagation(); handleFollow(u.username); }}
                    >
                      フォロー
                    </Button>
                  )
                ) : null
              }
              onClick={() => router.push(`/profile/${u.username}`)}
            >
              <ListItemText
                primary={
                  <Typography variant="subtitle1" fontWeight={600}>
                    {u.username}
                  </Typography>
                }
                secondary={
                  u.description ? (
                    <Typography variant="body2" color="text.secondary" noWrap>
                      {u.description}
                    </Typography>
                  ) : null
                }
              />
            </ListItem>
          ))}
          {users.length === 0 && (
            <Typography color="text.secondary" textAlign="center" py={4}>
              ユーザーが見つかりません
            </Typography>
          )}
        </List>
      </Container>
    </Box>
  );
}
