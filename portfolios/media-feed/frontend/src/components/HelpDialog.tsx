"use client";

import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, Typography, Box, Divider, List, ListItem, ListItemText,
} from "@mui/material";
import {
  TouchApp, SwipeVertical, Swipe as SwipeHorizontal, MoreVert,
  Search, Tag, People, LibraryBooks, Person,
} from "@mui/icons-material";

interface Props {
  open: boolean;
  onClose: () => void;
}

const FEED_OPERATIONS = [
  { icon: <SwipeVertical fontSize="small" />, label: "上下スワイプ", desc: "次・前のコンテンツに移動" },
  { icon: <TouchApp fontSize="small" />, label: "画面中央タップ", desc: "再生 / 一時停止" },
  { icon: <SwipeHorizontal fontSize="small" />, label: "左右スワイプ", desc: "コンテンツタイプを切り替え" },
  { icon: <MoreVert fontSize="small" />, label: "右側アイコン", desc: "保存・コメント・共有・音量調節" },
];

const PAGES = [
  { icon: <Search fontSize="small" />, label: "検索", desc: "タイトル・説明・タグでコンテンツを絞り込める" },
  { icon: <Tag fontSize="small" />, label: "タグ", desc: "タグ一覧からコンテンツを探せる" },
  { icon: <People fontSize="small" />, label: "ユーザー", desc: "登録ユーザーの一覧とフォロー機能" },
  { icon: <LibraryBooks fontSize="small" />, label: "記事", desc: "複数コンテンツをまとめた記事を閲覧できる" },
  { icon: <Person fontSize="small" />, label: "プロフィール", desc: "ブックマーク一覧の確認・フォロー中ユーザーの管理" },
];

export default function HelpDialog({ open, onClose }: Props) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{ sx: { bgcolor: "#111", borderRadius: 3 } }}
    >
      <DialogTitle sx={{ color: "primary.main", fontWeight: 700 }}>
        使い方ガイド
      </DialogTitle>
      <DialogContent>

        <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
          feedページの操作
        </Typography>
        <List dense disablePadding>
          {FEED_OPERATIONS.map(({ icon, label, desc }) => (
            <ListItem key={label} sx={{ px: 0, py: 0.5, gap: 1.5 }}>
              <Box sx={{ color: "primary.main", display: "flex", alignItems: "center", flexShrink: 0 }}>
                {icon}
              </Box>
              <ListItemText
                primary={label}
                secondary={desc}
                primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
                secondaryTypographyProps={{ variant: "caption", color: "text.secondary" }}
              />
            </ListItem>
          ))}
        </List>

        <Divider sx={{ borderColor: "#333", my: 2 }} />

        <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
          各ページの説明
        </Typography>
        <List dense disablePadding>
          {PAGES.map(({ icon, label, desc }) => (
            <ListItem key={label} sx={{ px: 0, py: 0.5, gap: 1.5 }}>
              <Box sx={{ color: "text.secondary", display: "flex", alignItems: "center", flexShrink: 0 }}>
                {icon}
              </Box>
              <ListItemText
                primary={label}
                secondary={desc}
                primaryTypographyProps={{ variant: "body2", fontWeight: 600 }}
                secondaryTypographyProps={{ variant: "caption", color: "text.secondary" }}
              />
            </ListItem>
          ))}
        </List>

      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} variant="contained" size="small">閉じる</Button>
      </DialogActions>
    </Dialog>
  );
}
