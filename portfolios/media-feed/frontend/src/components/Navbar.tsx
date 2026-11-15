"use client";

import { useState, useEffect } from "react";
import {
  AppBar, Toolbar, IconButton, Typography, Box, Button, Avatar,
  Drawer, List, ListItem, ListItemIcon, ListItemText, Divider,
  Menu, MenuItem,
} from "@mui/material";
import {
  Home as HomeIcon,
  Search as SearchIcon,
  Tag as TagIcon,
  Logout as LogoutIcon,
  People as PeopleIcon,
  Article as ArticleIcon,
  Menu as MenuIcon,
  Close as CloseIcon,
  LibraryBooks as LibraryBooksIcon,
  AdminPanelSettings as AdminIcon,
  WebAsset as BlogPartsIcon,
  BarChart as StatsIcon,
  HelpOutline as HelpIcon,
  MailOutline as MailIcon,
} from "@mui/icons-material";
import { useRouter, usePathname } from "next/navigation";
import { isLoggedIn, getUsername, logout, setUserPermissions, getUserPermissions, UserPermissions } from "@/lib/auth";
import { authApi } from "@/lib/api";
import HelpDialog from "@/components/HelpDialog";

const NAV_ITEMS = [
  { label: "フィード",   icon: <HomeIcon />,          path: "/feed" },
  { label: "検索",       icon: <SearchIcon />,        path: "/search" },
  { label: "タグ",       icon: <TagIcon />,           path: "/tags" },
  { label: "ユーザー",   icon: <PeopleIcon />,        path: "/users" },
  { label: "記事",       icon: <LibraryBooksIcon />,  path: "/articles" },
];

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const [loggedIn, setLoggedIn] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [adminAnchor, setAdminAnchor] = useState<null | HTMLElement>(null);
  const [perms, setPerms] = useState<UserPermissions>({ is_affiliate: false, is_uploader: false, is_author: false });
  const [helpOpen, setHelpOpen] = useState(false);

  useEffect(() => {
    const loggedInNow = isLoggedIn();
    setLoggedIn(loggedInNow);
    setUsername(getUsername());
    if (loggedInNow) {
      setPerms(getUserPermissions());
      authApi.me().then(({ data }) => {
        const p = { is_affiliate: data.is_affiliate, is_uploader: data.is_uploader, is_author: data.is_author };
        setUserPermissions(p);
        setPerms(p);
      }).catch(() => {});
    } else {
      setPerms({ is_affiliate: false, is_uploader: false, is_author: false });
    }
  }, [pathname]);

  const handleLogout = () => {
    logout();
    setLoggedIn(false);
    setUsername(null);
    setPerms({ is_affiliate: false, is_uploader: false, is_author: false });
    router.push("/feed");
  };

  const navigate = (path: string) => {
    router.push(path);
    setDrawerOpen(false);
  };

  return (
    <>
      <HelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
      <AppBar
        position="fixed"
        sx={{ background: "rgba(10,10,10,0.9)", backdropFilter: "blur(10px)", zIndex: 1200 }}
      >
        <Toolbar sx={{ gap: 1, minHeight: { xs: 52, sm: 64 } }}>
          {/* ハンバーガーメニュー（スマホのみ） */}
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setDrawerOpen(true)}
            size="small"
            sx={{ display: { sm: "none" } }}
          >
            <MenuIcon />
          </IconButton>

          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              cursor: "pointer",
              color: "primary.main",
              mr: { xs: 0, sm: 2 },
              fontSize: { xs: 15, sm: 20 },
              flexShrink: 0,
            }}
            onClick={() => router.push("/feed")}
          >
            StreamVault
          </Typography>

          {/* PC向けナビリンク */}
          <Box sx={{ display: { xs: "none", sm: "flex" }, gap: 0.5, flexGrow: 1 }}>
            {NAV_ITEMS.map(({ label, icon, path }) => (
              <IconButton
                key={path}
                color={pathname === path ? "primary" : "inherit"}
                onClick={() => router.push(path)}
                size="small"
                title={label}
              >
                {icon}
              </IconButton>
            ))}
          </Box>

          <Box sx={{ flexGrow: { xs: 1, sm: 0 } }} />

          {/* ヘルプ・お問い合わせ（常時表示） */}
          <Box sx={{ display: { xs: "none", sm: "flex" }, gap: 0 }}>
            <IconButton color="inherit" size="small" title="使い方" onClick={() => setHelpOpen(true)}>
              <HelpIcon fontSize="small" />
            </IconButton>
            <IconButton color="inherit" size="small" title="お問い合わせ" onClick={() => router.push("/contact")}>
              <MailIcon fontSize="small" />
            </IconButton>
          </Box>

          {loggedIn ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              {perms.is_author && (
                <IconButton
                  color="inherit"
                  onClick={() => router.push("/article/create")}
                  size="small"
                  title="記事作成"
                  sx={{ display: { xs: "none", sm: "flex" } }}
                >
                  <ArticleIcon fontSize="small" />
                </IconButton>
              )}
              {perms.is_affiliate && (
                <IconButton
                  color="inherit"
                  size="small"
                  title="管理"
                  sx={{ display: { xs: "none", sm: "flex" } }}
                  onClick={(e) => setAdminAnchor(e.currentTarget)}
                >
                  <AdminIcon fontSize="small" />
                </IconButton>
              )}
              <Menu
                anchorEl={adminAnchor}
                open={Boolean(adminAnchor)}
                onClose={() => setAdminAnchor(null)}
                PaperProps={{ sx: { bgcolor: "#1a1a1a", minWidth: 180 } }}
              >
                <MenuItem
                  onClick={() => { setAdminAnchor(null); router.push("/blog-parts"); }}
                  sx={{ gap: 1, fontSize: 14 }}
                >
                  <BlogPartsIcon fontSize="small" sx={{ color: "text.secondary" }} />
                  ブログパーツ作成
                </MenuItem>
                <MenuItem
                  onClick={() => { setAdminAnchor(null); router.push("/click-stats"); }}
                  sx={{ gap: 1, fontSize: 14 }}
                >
                  <StatsIcon fontSize="small" sx={{ color: "text.secondary" }} />
                  クリック集計
                </MenuItem>
              </Menu>
              <IconButton
                size="small"
                onClick={() => router.push(`/profile/${username}`)}
                sx={{ p: 0 }}
              >
                <Avatar sx={{ width: 30, height: 30, bgcolor: "primary.main", fontSize: 13 }}>
                  {username?.[0]?.toUpperCase()}
                </Avatar>
              </IconButton>
              <IconButton color="inherit" onClick={handleLogout} size="small" sx={{ display: { xs: "none", sm: "flex" } }}>
                <LogoutIcon fontSize="small" />
              </IconButton>
            </Box>
          ) : (
            <Button
              variant="contained"
              size="small"
              onClick={() => router.push("/login")}
              sx={{ borderRadius: 20, fontSize: { xs: 11, sm: 13 }, px: { xs: 1.5, sm: 2 } }}
            >
              ログイン
            </Button>
          )}
        </Toolbar>
      </AppBar>

      {/* スマホ用ドロワー */}
      <Drawer
        anchor="left"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{ sx: { width: 240, bgcolor: "#111" } }}
      >
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", p: 1.5 }}>
          <Typography variant="subtitle1" fontWeight={700} color="primary.main">
            StreamVault
          </Typography>
          <IconButton size="small" onClick={() => setDrawerOpen(false)} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
        <Divider sx={{ borderColor: "#222" }} />

        <List dense>
          {NAV_ITEMS.map(({ label, icon, path }) => (
            <ListItem
              key={path}
              onClick={() => navigate(path)}
              sx={{
                cursor: "pointer",
                bgcolor: pathname === path ? "primary.dark" : "transparent",
                "&:hover": { bgcolor: "#1e1e1e" },
                borderRadius: 1,
                mx: 0.5,
                my: 0.25,
              }}
            >
              <ListItemIcon sx={{ color: pathname === path ? "primary.main" : "text.secondary", minWidth: 36 }}>
                {icon}
              </ListItemIcon>
              <ListItemText primary={label} primaryTypographyProps={{ variant: "body2" }} />
            </ListItem>
          ))}
          <ListItem
            onClick={() => { setHelpOpen(true); setDrawerOpen(false); }}
            sx={{ cursor: "pointer", "&:hover": { bgcolor: "#1e1e1e" }, borderRadius: 1, mx: 0.5, my: 0.25 }}
          >
            <ListItemIcon sx={{ color: "text.secondary", minWidth: 36 }}>
              <HelpIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="使い方" primaryTypographyProps={{ variant: "body2" }} />
          </ListItem>
          <ListItem
            onClick={() => navigate("/contact")}
            sx={{ cursor: "pointer", "&:hover": { bgcolor: "#1e1e1e" }, borderRadius: 1, mx: 0.5, my: 0.25 }}
          >
            <ListItemIcon sx={{ color: "text.secondary", minWidth: 36 }}>
              <MailIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="お問い合わせ" primaryTypographyProps={{ variant: "body2" }} />
          </ListItem>
        </List>

        {loggedIn && (
          <>
            <Divider sx={{ borderColor: "#222", mt: 1 }} />
            <List dense>
              {perms.is_author && (
                <ListItem
                  onClick={() => navigate("/article/create")}
                  sx={{ cursor: "pointer", "&:hover": { bgcolor: "#1e1e1e" }, borderRadius: 1, mx: 0.5, my: 0.25 }}
                >
                  <ListItemIcon sx={{ color: "text.secondary", minWidth: 36 }}>
                    <ArticleIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText primary="記事作成" primaryTypographyProps={{ variant: "body2" }} />
                </ListItem>
              )}
              {perms.is_affiliate && (
                <>
                  <ListItem
                    onClick={() => navigate("/blog-parts")}
                    sx={{ cursor: "pointer", "&:hover": { bgcolor: "#1e1e1e" }, borderRadius: 1, mx: 0.5, my: 0.25 }}
                  >
                    <ListItemIcon sx={{ color: "text.secondary", minWidth: 36 }}>
                      <BlogPartsIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary="ブログパーツ作成" primaryTypographyProps={{ variant: "body2" }} />
                  </ListItem>
                  <ListItem
                    onClick={() => navigate("/click-stats")}
                    sx={{ cursor: "pointer", "&:hover": { bgcolor: "#1e1e1e" }, borderRadius: 1, mx: 0.5, my: 0.25 }}
                  >
                    <ListItemIcon sx={{ color: "text.secondary", minWidth: 36 }}>
                      <StatsIcon fontSize="small" />
                    </ListItemIcon>
                    <ListItemText primary="クリック集計" primaryTypographyProps={{ variant: "body2" }} />
                  </ListItem>
                </>
              )}
              <ListItem
                onClick={() => { navigate(`/profile/${username}`); }}
                sx={{ cursor: "pointer", "&:hover": { bgcolor: "#1e1e1e" }, borderRadius: 1, mx: 0.5, my: 0.25 }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>
                  <Avatar sx={{ width: 22, height: 22, bgcolor: "primary.main", fontSize: 11 }}>
                    {username?.[0]?.toUpperCase()}
                  </Avatar>
                </ListItemIcon>
                <ListItemText primary={username} primaryTypographyProps={{ variant: "body2" }} />
              </ListItem>
              <ListItem
                onClick={() => { handleLogout(); setDrawerOpen(false); }}
                sx={{ cursor: "pointer", "&:hover": { bgcolor: "#1e1e1e" }, borderRadius: 1, mx: 0.5, my: 0.25 }}
              >
                <ListItemIcon sx={{ color: "text.secondary", minWidth: 36 }}>
                  <LogoutIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText primary="ログアウト" primaryTypographyProps={{ variant: "body2" }} />
              </ListItem>
            </List>
          </>
        )}
      </Drawer>
    </>
  );
}
