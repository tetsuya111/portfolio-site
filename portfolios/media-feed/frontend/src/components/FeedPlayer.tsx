"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Box, IconButton, Typography, Chip, Stack, Drawer,
  TextField, Button, List, ListItem, ListItemText, Avatar,
  CircularProgress, Snackbar,
} from "@mui/material";
import {
  Bookmark as BookmarkIcon,
  BookmarkBorder as BookmarkBorderIcon,
  Comment as CommentIcon,
  Share as ShareIcon,
  VolumeOff, VolumeUp,
  Close as CloseIcon,
} from "@mui/icons-material";
import { BASE_URL, Content, bookmarkApi, commentsApi, Comment, contentsApi, AdContent, adContentApi, getMediaUrl } from "@/lib/api";
import VideoPool from "@/components/feed/VideoPool";
import { resolvePreloadTarget, shouldPreload } from "@/components/feed/resolveNext";
import { isLoggedIn, getUsername } from "@/lib/auth";
import { randomUUID } from 'crypto';

interface FeedPlayerProps {
  initialContents: Content[];
  totalCount: number;
  queryParams?: Record<string, string | string[]>;
  onClose?: () => void;
}

function getZone(x: number, y: number): number {
  const relY = y / window.innerHeight;
  if (relY < 0.25) return 1;
  if (relY >= 0.75) return 5;
  const relX = x / window.innerWidth;
  if (relX < 1 / 3) return 2;
  if (relX >= 2 / 3) return 4;
  return 3;
}

const TYPE_OPTIONS = [
  { label: "すべて",   value: "" },
  { label: "動画",     value: "video" },
  { label: "画像",     value: "image" },
  { label: "美女動画",  value: "dmm_video" },
  { label: "美女画像",  value: "dmm_image" },
  { label: "マニア動画", value: "duga_video" },
] as const;

type ContentTypeFilter = "" | "video" | "image" | "dmm_video" | "dmm_image" | "duga_video";

export default function FeedPlayer({ initialContents, totalCount, queryParams, onClose }: FeedPlayerProps) {
  const router = useRouter();
  const urlSearchParams = useSearchParams();
  const resolvedQueryParams = useMemo<Record<string, string | string[]>>(() => {
    if (queryParams !== undefined) return queryParams;
    const p: Record<string, string | string[]> = { random: "true" };
    const type = urlSearchParams.get("type");
    const tag = urlSearchParams.get("tag");
    const q = urlSearchParams.get("q");
    const random = urlSearchParams.get("random");
    if (type) p.type = type;
    if (tag) p.tag = tag;
    if (q) p.q = q;
    if (random === "false") delete p.random;
    return p;
  }, [queryParams, urlSearchParams]);
  const [contents, setContents] = useState<Content[]>(initialContents);
  const [total, setTotal] = useState(totalCount);
  const [index, setIndex] = useState(0);
  const [uiVisible, setUiVisible] = useState(true);
  const [muted, setMuted] = useState(false);
  const [videoPaused, setVideoPaused] = useState(false);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [bookmarkIdMap, setBookmarkIdMap] = useState<Map<string, string>>(new Map());
  const [commentOpen, setCommentOpen] = useState(false);
  const [commentListOpen, setCommentListOpen] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [snackbar, setSnackbar] = useState("");
  const [shareOpen, setShareOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [currentOverride, setCurrentOverride] = useState<Content | null>(null);
  const [showInfo, setShowInfo] = useState(false);
  const [showAllTags, setShowAllTags] = useState(false);
  const [contentType, setContentType] = useState<ContentTypeFilter>("");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const touchStart = useRef<{ x: number; y: number; time: number } | null>(null);
  const loggedIn = isLoggedIn();
  const username = getUsername();
  const current = currentOverride ?? contents[index];
  const bookmarked = current ? bookmarkedIds.has(current.id) : false;
  const bookmarkId = current ? (bookmarkIdMap.get(current.id) ?? null) : null;
  const [adContents, setAdContents] = useState<AdContent[]>([]);
  const [currentAd, setCurrentAd] = useState<AdContent | null>(null);
  const [adSize, setAdSize] = useState<{ width: number; height: number } | null>(null);
  const adMapRef = useRef<Map<number, AdContent>>(new Map());
  const adTargetIndexRef = useRef(-1);
  const adPoolIdxRef = useRef(0);
  const realViewCountRef = useRef(0);
  const [seriesMap,setSeriesMap]=useState(getSeriesMap(contents));


  function getSeriesMap(contents:Content[]){
    //{<content id> :<series id>}
    const response:any[]=[];
    const history:any[]=[];
    let current_key:string="";
    contents.forEach((content:Content,index:number)=>{
      const sid:string|null|undefined=content.detail?.series_id;
      let key=sid?sid : content.id;

      //同じシリーズが後方でまたでてきたとき
      if(history.indexOf(key) !=-1){
        let suffix=Math.random().toString(36).slice(2) + Date.now().toString(36);
        key=`${key}_${suffix}`;
        if(contents[index].detail != undefined){
          contents[index].detail.series_id=key;
          console.log(`rewrite ${contents[index].detail.series_id} ${current_key}`);
        }
      
        //同じシリーズのとき、コンテンツのシリーズIDを一時的に書き換える
      }
      current_key=key;
      history.push(key);
      response.push(key);
      /*
      console.log("series map key : "+content.id);
      console.log("series map value : "+sid);
      console.log(JSON.stringify(content));
      */
    });
    return response;
  }
  const setContents2=useCallback((contents:Content[])=>{
    setContents(contents);
    setSeriesMap(getSeriesMap(contents));
  },[setContents,setSeriesMap]);
  
  const fetchInitialContents = useCallback(async ()=>{
    const params={ ...resolvedQueryParams, random: "true" };
    const { data } = await contentsApi.list(params);
    setContents2(data.results);
    setTotal(data.count);
  },[resolvedQueryParams,setContents2]);
  if(contents.length == 0){
    fetchInitialContents();
  }


  // シリーズID単位でユニーク化した件数計算
  const seriesKeys = seriesMap.reduce<string[]>((acc, key) => {
    if (!acc.includes(key)) acc.push(key);
    return acc;
  }, []);
  const currentSeriesKey = (() => {
    const content=contents[index];
    if(!content) return null;
    return content?.detail?.series_id ? content.detail?.series_id : content.id;
  })();
  
  const seriesIndex = currentSeriesKey === null ? -1 : seriesKeys.indexOf(currentSeriesKey);
  console.log("キー "+currentSeriesKey+JSON.stringify(seriesMap));
  console.log(JSON.stringify(seriesKeys));
  console.log("シリーズ "+seriesIndex);

  const resetHideTimer = useCallback(() => {
    setUiVisible(true);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => setUiVisible(false), 3000);
  }, []);

  useEffect(() => {
    adContentApi.list({ number: 10, random: true }).then(({ data }) => {
      setAdContents(data);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!currentAd?.width || !currentAd?.height) {
      setAdSize(null);
      return;
    }
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const scale = Math.min(vw / currentAd.width, vh / currentAd.height) * 0.8;
    setAdSize({
      width: Math.round(currentAd.width * scale),
      height: Math.round(currentAd.height * scale),
    });
  }, [currentAd]);

  useEffect(() => {
    if (!currentAd) return;
    const nextIndex = index + 1;
    const timer = setTimeout(() => { goTo(nextIndex); }, 5000);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentAd]);

  useEffect(() => {
    resetHideTimer();
    return () => { if (hideTimer.current) clearTimeout(hideTimer.current); };
  }, [index, resetHideTimer]);

  useEffect(() => {
    setShowAllTags(false);
  }, [index, currentOverride]);

  useEffect(() => {
    if (!loggedIn || !username) return;
    bookmarkApi.list(username).then(({ data }) => {
      setBookmarkedIds(new Set(data.map((b) => b.content.id)));
      setBookmarkIdMap(new Map(data.map((b) => [b.content.id, b.id])));
    }).catch(() => {});
  }, [loggedIn, username]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowUp") goTo(index - 1);
      if (e.key === "ArrowDown") goTo(index + 1);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });

  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.deltaY > 0) goTo(index + 1);
      else goTo(index - 1);
    };
    window.addEventListener("wheel", handleWheel, { passive: false });
    return () => window.removeEventListener("wheel", handleWheel);
  });

  const buildTypeParams = useCallback((base: Record<string, string | string[]>, type: ContentTypeFilter) => {
    const p = { ...base };
    if (type === "video")      { p.type = "video"; p.exclude_user = ["DMM", "DUGA"]; }
    else if (type === "image") { p.type = "image"; p.exclude_user = ["DMM", "DUGA"]; }
    else if (type === "dmm_video") { p.user = "DMM"; p.type = "video"; p.random = "true"; }
    else if (type === "dmm_image") { p.user = "DMM"; p.type = "image"; p.random = "true"; }
    else if (type === "duga_video") { p.user = "DUGA"; p.type = "video"; p.random = "true"; }
    return p;
  }, []);

  const goTo = useCallback(async (targetIndex: number) => {
    if (targetIndex < 0) return;

    const goingForward = targetIndex > index;
    // 広告表示中 → 方向に応じてナビゲーション
    if (currentAd) {
      const adTarget = adTargetIndexRef.current;
      setCurrentAd(null);
      adTargetIndexRef.current = -1;
      if (goingForward && adTarget >= 0) {
        // 上スクロール(前進): 予定されていたコンテンツへ
        setIndex(adTarget);
      }
      else{
        setIndex(adTarget-1);
      }
      // 下スクロール(後退): 以前のコンテンツに留まる
      return;
    }

    setCurrentOverride(null);
    setShowInfo(false);
    console.log(`targetIndex : ${targetIndex},contents.length : ${contents.length},total : ${total}`)

    let currentContents = contents;
    if (targetIndex >= contents.length) {
      setLoading(true);
      try {
        if (contents.length >= total) {
          // 全件取得済み → 同条件でランダムにリセット
          console.log("AAA");
          const params = buildTypeParams({ ...resolvedQueryParams, random: "true" }, contentType);
          const { data } = await contentsApi.list(params);
          setContents2(data.results);
          setTotal(data.count);
          setPage(1);
          setIndex(0);
          setCurrentOverride(null);
          setShowInfo(false);
          setLoading(false);
          return;
        } else {
          console.log("BBB");
          const nextPage = page + 1;
          const baseParams = { ...resolvedQueryParams };
          delete baseParams.random;
          const params = buildTypeParams({ ...baseParams, page: String(nextPage),random:"true" }, contentType);
          const { data } = await contentsApi.list(params);
          console.log("next contents api");
          const merged = [...contents, ...data.results];
          setContents2(merged);
          setPage(nextPage);
          currentContents = merged;
        }
      } finally {
        setLoading(false);
      }
    }

    const prevContent = currentOverride ?? contents[index];
    const prevSeriesId = prevContent?.detail?.series_id;
    const direction = targetIndex > index ? 1 : -1;

    // skip contents that share the same series_id as the previous content
    let finalIndex = Math.min(targetIndex, currentContents.length - 1);
    while (finalIndex >= 0 && finalIndex < currentContents.length) {
      const sid = currentContents[finalIndex]?.detail?.series_id;
      if (!sid || sid === '-1' || sid !== prevSeriesId) break;
      finalIndex += direction;
    }
    if (finalIndex < 0 || finalIndex >= currentContents.length){
      //そのシリーズがコンテンツ一覧の最後のとき
       return goTo(finalIndex);
    }

    // 広告マップを確認: このコンテンツに対応する広告があれば表示
    console.log("finalIndex "+finalIndex);
    if(adContents.length > 0){
      if (adMapRef.current.has(finalIndex)) {
        adTargetIndexRef.current = finalIndex;
        setCurrentAd(adMapRef.current.get(finalIndex)!);
        return;
      }else if(!goingForward && adMapRef.current.has(finalIndex+1)){
        adTargetIndexRef.current = finalIndex+1;
        setCurrentAd(adMapRef.current.get(finalIndex+1)!);
        return;
      }
    }

    // コンテンツN件ごとに広告を新規登録して表示
    if(goingForward){
      const ad_per_content_count = 5;
      realViewCountRef.current++;
      if (realViewCountRef.current % ad_per_content_count === 0 && adContents.length > 0) {
        const idx = adPoolIdxRef.current % adContents.length;
        adPoolIdxRef.current++;
        const selectedAd = adContents[idx];
        adMapRef.current.set(finalIndex, selectedAd);
        adTargetIndexRef.current = finalIndex;
        setCurrentAd(selectedAd);
        return;
      }
    }

    setIndex(finalIndex);

    // show random item from the new series when series_id changes
    console.log(`finalIndex : ${finalIndex}`);
    const newContent = currentContents[finalIndex];
    const newSeriesId = newContent?.detail?.series_id;
    if (newSeriesId && newSeriesId !== '-1' && newSeriesId !== prevSeriesId) {
      try {
        const { data } = await contentsApi.getBySeriesRandom(newSeriesId);
        console.log("series contents api");
        if (data.results.length > 0) setCurrentOverride(data.results[0]);
      } catch {}
    }
  }, [contents, total, page, resolvedQueryParams, contentType, index, currentOverride, buildTypeParams, currentAd, adContents]);

  const switchType = async (type: ContentTypeFilter) => {
    setContentType(type);
    setCurrentAd(null);
    adMapRef.current.clear();
    adTargetIndexRef.current = -1;
    realViewCountRef.current = 0;
    adPoolIdxRef.current = 0;
    setLoading(true);
    try {
      const params = buildTypeParams({ ...resolvedQueryParams }, type);
      const { data } = await contentsApi.list(params);
      setContents2(data.results);
      setTotal(data.count);
      setIndex(0);
      setPage(1);
      setCurrentOverride(null);
      setShowInfo(false);
    } finally {
      setLoading(false);
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    const t = e.touches[0];
    touchStart.current = { x: t.clientX, y: t.clientY, time: Date.now() };
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStart.current) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touchStart.current.x;
    const dy = t.clientY - touchStart.current.y;
    const elapsed = Date.now() - touchStart.current.time;
    if (Math.abs(dy) > 50 && Math.abs(dy) > Math.abs(dx)) {
      // 上下スワイプ: 広告中も含めてコンテンツ移動
      if (dy < 0) goTo(index + 1);
      else goTo(index - 1);
    } else if (!currentAd) {
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy)) {
        // 左右スワイプ: 左右クリックと同じ挙動
        if (dx > 0) handleZoneAction(4); // 右スワイプ → zone4(右クリック)
        else        handleZoneAction(2); // 左スワイプ → zone2(左クリック)
      } else if (Math.abs(dx) < 30 && Math.abs(dy) < 30 && elapsed < 300) {
        const target = document.elementFromPoint(t.clientX, t.clientY);
        if (
          target?.closest("button") ||
          target?.closest("a") ||
          target?.closest('[role="button"]')
        ) {
          touchStart.current = null;
          resetHideTimer();
          return;
        }
        const zone = getZone(touchStart.current.x, touchStart.current.y);
        handleZoneAction(zone);
      }
    }
    touchStart.current = null;
    resetHideTimer();
  };

  const handleZoneAction = async (zone: number) => {
    // 情報表示中はどこでもタップで閉じる
    if (showInfo) {
      setShowInfo(false);
      return;
    }
    if (zone === 1) {
      if (current?.source_url) window.open(current.source_url, "_blank");
    } else if (zone === 2) {
      const detail = current?.detail;
      if (detail) {
        try {
          if (detail.series_number > 0) {
            const { data } = await contentsApi.getBySeries(detail.series_id, detail.series_number - 1);
            if (data.results.length > 0) setCurrentOverride(data.results[0]);
          } else {
            // series_number === 0 → 同シリーズの最大番号を取得
            const { data } = await contentsApi.list({ series_id: detail.series_id });
            if (data.results.length > 0) {
              const maxItem = data.results.reduce((a, b) =>
                (b.detail?.series_number ?? -1) > (a.detail?.series_number ?? -1) ? b : a
              );
              setCurrentOverride(maxItem);
            }
          }
        } catch {}
      }
    } else if (zone === 3) {
      if (current?.type === "video") toggleVideoPlay();
      else if (current?.source_url) window.open(current.source_url, "_blank");
    } else if (zone === 4) {
      const detail = current?.detail;
      if (detail) {
        try {
          const { data: nextData } = await contentsApi.getBySeries(detail.series_id, detail.series_number + 1);
          if (nextData.results.length > 0) {
            setCurrentOverride(nextData.results[0]);
          } else {
            // 最大番号 → シリーズ番号0に戻る
            const { data: zeroData } = await contentsApi.getBySeries(detail.series_id, 0);
            if (zeroData.results.length > 0) setCurrentOverride(zeroData.results[0]);
          }
        } catch {}
      }
    } else if (zone === 5) {
      setShowInfo(true);
    }
  };

  const handleMouseClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest("button") || target.closest("a")) return;
    resetHideTimer();
    const zone = getZone(e.clientX, e.clientY);
    handleZoneAction(zone);
  };

  const toggleVideoPlay = () => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
      setVideoPaused(false);
    } else {
      videoRef.current.pause();
      setVideoPaused(true);
    }
  };

  const toggleBookmark = async () => {
    if (!loggedIn || !username) { setSnackbar("ログインが必要です"); return; }
    if (bookmarked && bookmarkId) {
      await bookmarkApi.remove(username, bookmarkId);
      setBookmarkedIds((prev) => { const next = new Set(prev); next.delete(current.id); return next; });
      setBookmarkIdMap((prev) => { const next = new Map(prev); next.delete(current.id); return next; });
    } else {
      const { data } = await bookmarkApi.add(username, current.id);
      setBookmarkedIds((prev) => new Set([...prev, current.id]));
      setBookmarkIdMap((prev) => new Map([...prev, [current.id, data.id]]));
    }
  };

  const openComments = async () => {
    const { data } = await commentsApi.list(current.id);
    setComments(data);
    setCommentListOpen(true);
  };

  const submitComment = async () => {
    if (!newComment.trim()) return;
    const { data } = await commentsApi.add(current.id, newComment);
    setComments((prev) => [data, ...prev]);
    setNewComment("");
    setCommentOpen(false);
    setShowInfo(false);
  };

  const handleShare = () => setShareOpen(true);

  const handleVideoEnded = useCallback(() => {
    goTo(index + 1);
  }, [goTo, index]);

  const mediaUrl = current ? getMediaUrl(current) : "";

  // 次に実際に表示されるコンテンツ（シリーズスキップ・広告挿入を考慮済み）を先読みする。
  const preloadTarget = useMemo(() => {
    if (!current || currentAd) return null;
    if (!shouldPreload()) return null;
    return resolvePreloadTarget(contents, index, adMapRef.current, current?.detail?.series_id);
  }, [contents, index, current, currentAd]);

  const previousContent = index > 0 ? contents[index - 1] ?? null : null;
  /*
    const mediaUrl = (() => {
    if (!current) return "";

    const path = (current.path ?? "").trim();
    if (path) {
      if (/^https?:\/\//i.test(path)) return path;
      return `/api/contents/${current.id}/media/`;
    }

    const link = (current.link ?? "").trim();
    if (!link) return "";
    if (/^https?:\/\//i.test(link)) return link;
    if (link.startsWith("//")) return `https:${link}`;
    if (link.startsWith("/")) {
      const apiRoot = BASE_URL.endsWith("/api") ? BASE_URL.slice(0, -4) : BASE_URL;
      return `${apiRoot}${link}`;
    }
    return link;
  })();
  */

  useEffect(()=>{
    const currentAdArea=document.getElementById("current-ad-area");
    if(!currentAdArea||!currentAd)
      return;
    const html=currentAd.html;
    const tmp_e=document.createElement("div");
    tmp_e.innerHTML=html; //一時エレメントに追加
    Array.from(tmp_e.children).forEach((e)=>{
      if(e.tagName.toLowerCase() === "script"){
        const newScript=document.createElement("script");
        Array.from(e.attributes).forEach(attr=>{
          newScript.setAttribute(attr.name,attr.value);
        });
        newScript.textContent=e.textContent;
        currentAdArea.appendChild(newScript);
      }
      else{
        currentAdArea.appendChild(e);
      }
    });
    tmp_e.remove();
    //currentAdArea.innerHTML=currentAd.html;
  },[currentAd]);

  const switcherTop = onClose ? 0 : 64;

  return (
    <Box
      sx={{ height: "100vh", width: "100vw", background: "#000", position: "relative", overflow: "hidden" }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onClick={currentAd ? undefined : handleMouseClick}
    >
      {/* Content type switcher — always visible */}
      <Box
        sx={{
          position: "fixed", top: switcherTop, left: 0, right: 0, zIndex: 1100,
          display: "flex", alignItems: "center", justifyContent: "center", gap: 1, py: 0.75,
          bgcolor: "rgba(0,0,0,0.6)", backdropFilter: "blur(6px)",
        }}
      >
        {onClose && (
          <IconButton
            size="small"
            sx={{ color: "white", position: "absolute", left: 8 }}
            onClick={(e) => { e.stopPropagation(); onClose(); }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        )}
        {TYPE_OPTIONS.map(({ label, value }) => (
          <Chip
            key={value}
            label={label}
            size="small"
            clickable
            onClick={(e) => { e.stopPropagation(); switchType(value); }}
            sx={{
              color: contentType === value ? "white" : "rgba(255,255,255,0.6)",
              bgcolor: contentType === value ? "primary.main" : "rgba(255,255,255,0.08)",
              fontWeight: contentType === value ? 700 : 400,
              "&:hover": { bgcolor: "primary.dark" },
            }}
          />
        ))}
      </Box>

      {/* source_url open button */}
      {!currentAd && current?.source_url && (
        <Button
          variant="contained"
          onClick={(e) => { e.stopPropagation(); window.open(current.source_url, "_blank"); }}
          sx={{
            position: "fixed",
            top: switcherTop + 44,
            left: 8,
            zIndex: 1100,
            bgcolor: "#e01010",
            color: "#fff",
            fontWeight: 900,
            fontSize: 14,
            px: 1.5,
            py: 0.4,
            borderRadius: 1,
            boxShadow: "0 5px 0 #8b0000, 0 7px 10px rgba(0,0,0,0.45)",
            letterSpacing: "0.05em",
            "&:hover": {
              bgcolor: "#c00d0d",
              boxShadow: "0 3px 0 #8b0000, 0 4px 8px rgba(0,0,0,0.4)",
              transform: "translateY(2px)",
            },
            "&:active": {
              boxShadow: "0 1px 0 #8b0000",
              transform: "translateY(4px)",
            },
            transition: "transform 0.08s, box-shadow 0.08s",
          }}
        >
          サイトへ
        </Button>
      )}

      {!current ? (
        <Box sx={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Typography color="text.secondary">コンテンツがありません</Typography>
        </Box>
      ) : (
        <>
      {/* 広告スロット */}
      {currentAd ? (
        <Box sx={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#000", overflow: "hidden" }}>
          <Box
            id="current-ad-area"
            sx={{
              width: adSize ? adSize.width : "80%",
              height: adSize ? adSize.height : "80%",
              "& *": {
                width: "100% !important",
                maxWidth: "100% !important",
                height: "100% !important",
                maxHeight: "100% !important",
              },
            }}
          />
        </Box>
      ) : current.type === "video" ? (
        <VideoPool
          current={current}
          next={preloadTarget}
          previous={previousContent}
          muted={muted}
          onEnded={handleVideoEnded}
          videoRef={videoRef}
        />
      ) : (
        <Box
          component="img"
          src={mediaUrl}
          alt={current.title}
          sx={{ width: "100%", height: "100%", objectFit: "contain" }}
        />
      )}

      {/* Info overlay (zone 5) */}
      {showInfo && (
        <Box
          sx={{
            position: "absolute", inset: 0, display: "flex", alignItems: "center",
            justifyContent: "center", bgcolor: "rgba(0,0,0,0.75)", p: 3, zIndex: 10,
          }}
        >
          <Box sx={{ color: "white", maxWidth: 600, width: "100%" }}>
            <IconButton
              sx={{ position: "absolute", top: 16, right: 16, color: "white" }}
              onClick={(e) => { e.stopPropagation(); setShowInfo(false); }}
            >
              <CloseIcon />
            </IconButton>
            <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>{current.title}</Typography>
            {current.description && (
              <Typography variant="body2" sx={{ color: "#ddd", whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>
                {current.description}
              </Typography>
            )}
          </Box>
        </Box>
      )}

      {/* UI overlay */}
      <Box
        sx={{
          position: "absolute", inset: 0,
          opacity: uiVisible && !currentAd ? 1 : 0,
          transition: "opacity 0.4s",
          pointerEvents: uiVisible && !currentAd ? "auto" : "none",
        }}
      >
        {/* Right side buttons */}
        <Box sx={{
          position: "absolute", right: 12, bottom: 120,
          display: "flex", flexDirection: "column", alignItems: "center", gap: 2,
        }}>
          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <IconButton
              sx={{ color: "white" }}
              onClick={(e) => { e.stopPropagation(); toggleBookmark(); }}
              onContextMenu={(e) => e.preventDefault()}
            >
              {bookmarked ? <BookmarkIcon color="primary" fontSize="large" /> : <BookmarkBorderIcon fontSize="large" />}
            </IconButton>
            <Typography variant="caption" color="white">保存</Typography>
          </Box>

          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <IconButton
              sx={{ color: "white" }}
              onClick={(e) => { e.stopPropagation(); setCommentOpen(true); }}
              onContextMenu={(e) => { e.preventDefault(); openComments(); }}
            >
              <CommentIcon fontSize="large" />
            </IconButton>
            <Typography variant="caption" color="white">
              {comments.length || ""}
            </Typography>
          </Box>

          <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <IconButton sx={{ color: "white" }} onClick={(e) => { e.stopPropagation(); handleShare(); }}>
              <ShareIcon fontSize="large" />
            </IconButton>
            <Typography variant="caption" color="white">共有</Typography>
          </Box>

          {current.type === "video" && (
            <IconButton
              sx={{ color: "white" }}
              onClick={(e) => { e.stopPropagation(); setMuted((m) => !m); }}
            >
              {muted ? <VolumeOff fontSize="large" /> : <VolumeUp fontSize="large" />}
            </IconButton>
          )}
        </Box>

        {/* Bottom info */}
        <Box sx={{
          position: "absolute", bottom: 0, left: 0, right: 0, p: 2,
          background: "linear-gradient(transparent, rgba(0,0,0,0.85))",
        }}>
          {current.user && (
            <Typography variant="caption" sx={{ color: "#aaa", display: "block", mb: 0.5 }}>
              @{current.user}
            </Typography>
          )}
          <Typography variant="subtitle1" sx={{ color: "white", fontWeight: 600, mb: 0.5 }}>
            {current.title}
          </Typography>
          {(() => {
            const allTags = Array.isArray(current.tags) ? current.tags : [];
            const displayTags = showAllTags ? allTags : allTags.slice(0, 5);
            const hasMore = allTags.length > 5;
            return (
              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                {displayTags.map((tag) => (
                  <Chip
                    key={tag.name}
                    label={`#${tag.name}`}
                    size="small"
                    clickable
                    sx={{
                      bgcolor: "rgba(255,68,88,0.3)",
                      color: "white",
                      fontSize: 11,
                      height: 22,
                      "&:hover": { bgcolor: "primary.main" },
                    }}
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      router.push(`/search?tag=${encodeURIComponent(tag.name)}`);
                    }}
                  />
                ))}
                {hasMore && (
                  <Chip
                    label={showAllTags ? "閉じる" : "..."}
                    size="small"
                    clickable
                    sx={{
                      bgcolor: "rgba(255,255,255,0.15)",
                      color: "white",
                      fontSize: 11,
                      height: 22,
                      "&:hover": { bgcolor: "rgba(255,255,255,0.3)" },
                    }}
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      setShowAllTags((prev) => !prev);
                    }}
                  />
                )}
              </Stack>
            );
          })()}
        </Box>

        {/* Index indicator (シリーズ単位) */}
        <Typography
          variant="caption"
          sx={{ position: "absolute", top: 112, left: "50%", transform: "translateX(-50%)", color: "#666" }}
        >
          {seriesIndex + 1} / {seriesKeys.length}{contents.length < total ? "+" : ""}
        </Typography>
      </Box>

      {loading && (
        <Box sx={{ position: "absolute", bottom: 60, left: "50%", transform: "translateX(-50%)" }}>
          <CircularProgress size={20} />
        </Box>
      )}

      {/* Comment input drawer */}
      <Drawer anchor="bottom" open={commentOpen} onClose={() => setCommentOpen(false)}>
        <Box sx={{ p: 2, bgcolor: "background.paper" }}>
          <TextField
            fullWidth
            multiline
            rows={2}
            placeholder="コメントを入力..."
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            variant="outlined"
            size="small"
          />
          <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 1, gap: 1 }}>
            <Button onClick={() => setCommentOpen(false)}>キャンセル</Button>
            <Button variant="contained" onClick={submitComment}>送信</Button>
          </Box>
        </Box>
      </Drawer>

      {/* Comment list drawer */}
      <Drawer anchor="bottom" open={commentListOpen} onClose={() => setCommentListOpen(false)}>
        <Box sx={{ p: 2, bgcolor: "background.paper", maxHeight: "60vh", overflow: "auto" }}>
          <Typography variant="h6" sx={{ mb: 1 }}>コメント</Typography>
          <List dense>
            {comments.map((c) => (
              <ListItem key={c.id} alignItems="flex-start">
                <Avatar sx={{ width: 28, height: 28, mr: 1, bgcolor: "primary.main", fontSize: 12 }}>
                  {c.username[0]?.toUpperCase()}
                </Avatar>
                <ListItemText
                  primary={c.username}
                  secondary={c.text}
                  primaryTypographyProps={{ variant: "caption", fontWeight: 600 }}
                />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>

      {/* Share drawer */}
      <Drawer anchor="bottom" open={shareOpen} onClose={() => setShareOpen(false)}>
        <Box sx={{ p: 2, bgcolor: "background.paper" }}>
          <Typography variant="h6" sx={{ mb: 1 }}>共有</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {[
              { label: "Twitter/X", url: `https://twitter.com/intent/tweet?text=${encodeURIComponent(`🎬 ${current.title}\n\n${current.source_url || current.link}`)}&url=${encodeURIComponent(current.source_url || current.link)}` },
              { label: "LINE", url: `https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(current.link)}` },
            ].map((s) => (
              <Button
                key={s.label}
                variant="outlined"
                size="small"
                onClick={() => window.open(s.url, "_blank")}
              >
                {s.label}
              </Button>
            ))}
            <Button
              variant="outlined"
              size="small"
              onClick={() => { navigator.clipboard.writeText(current.link); setSnackbar("URLをコピーしました"); setShareOpen(false); }}
            >
              URLコピー
            </Button>
          </Stack>
        </Box>
      </Drawer>

      <Snackbar
        open={!!snackbar}
        autoHideDuration={2000}
        onClose={() => setSnackbar("")}
        message={snackbar}
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
      />
        </>
      )}
    </Box>
  );
}
