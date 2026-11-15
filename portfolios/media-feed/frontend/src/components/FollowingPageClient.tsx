"use client";

import { Box, Container, Typography, List, ListItem, ListItemAvatar, Avatar, ListItemText, Button, Divider } from "@mui/material";
import { useRouter } from "next/navigation";
import { FollowingUser, followingApi } from "@/lib/api";
import { useState, useEffect } from "react";
import { getUsername, isLoggedIn } from "@/lib/auth";

interface Props {
  username: string;
}

export default function FollowingPageClient({ username }: Props) {
  const router = useRouter();
  const [users, setUsers] = useState<FollowingUser[]>([]);
  const currentUser = getUsername();
  const isOwner = currentUser === username;

  useEffect(() => {
    followingApi.list(username)
      .then(({ data }) => setUsers(data.following_users))
      .catch(() => {});
  }, [username]);

  const unfollow = async (target: string) => {
    if (!isOwner || !currentUser) return;
    await followingApi.unfollow(currentUser, target);
    setUsers((prev) => prev.filter((u) => u.username !== target));
  };

  return (
    <Box sx={{ pt: 10, minHeight: "100vh", bgcolor: "background.default" }}>
      <Container maxWidth="sm" sx={{ py: 3 }}>
        <Typography variant="h5" fontWeight={700} sx={{ mb: 3 }}>
          {username} のフォロー中
        </Typography>

        {users.length === 0 ? (
          <Typography color="text.secondary" textAlign="center" py={4}>
            フォロー中のユーザーがいません
          </Typography>
        ) : (
          <List sx={{ bgcolor: "background.paper", borderRadius: 2 }}>
            {users.map((u, i) => (
              <Box key={u.username}>
                <ListItem
                  secondaryAction={
                    isOwner ? (
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        onClick={() => unfollow(u.username)}
                      >
                        フォロー解除
                      </Button>
                    ) : (
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => router.push(`/profile/${u.username}`)}
                      >
                        プロフィール
                      </Button>
                    )
                  }
                >
                  <ListItemAvatar>
                    <Avatar
                      sx={{ bgcolor: "primary.main", cursor: "pointer" }}
                      onClick={() => router.push(`/profile/${u.username}`)}
                    >
                      {u.username[0]?.toUpperCase()}
                    </Avatar>
                  </ListItemAvatar>
                  <ListItemText
                    primary={u.username}
                    sx={{ cursor: "pointer" }}
                    onClick={() => router.push(`/profile/${u.username}`)}
                  />
                </ListItem>
                {i < users.length - 1 && <Divider />}
              </Box>
            ))}
          </List>
        )}
      </Container>
    </Box>
  );
}
